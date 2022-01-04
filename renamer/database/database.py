from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session
import os
import threading
import asyncio
from sqlalchemy import Column, Integer, Boolean, String, ForeignKey, UniqueConstraint, func
from ..config import Config
import motor.motor_asyncio


def start() -> scoped_session:
    engine = create_engine(Config.DATABASE_URL, client_encoding="utf8")
    BASE.metadata.bind = engine
    BASE.metadata.create_all(engine)
    return scoped_session(sessionmaker(bind=engine, autoflush=False))
BASE = declarative_base()
SESSION = start()
INSERTION_LOCK = threading.RLock()
class Database(BASE):
    __tablename__ = "database"
    id = Column(Integer, primary_key=True)
    thumb_id = Column(Integer)
    upload_mode = Column(Boolean)
    is_logged = Column(Boolean)
    def __init__(self, id, thumb_id, upload_mode, is_logged):
        self.id = id
        self.thumb_id = thumb_id
        self.upload_mode = upload_mode
        self.is_logged = is_logged
Database.__table__.create(checkfirst=True)
async def update_login(id, is_logged):
    with INSERTION_LOCK:
        msg = SESSION.query(Database).get(id)
        if not msg:
            msg = Database(id, None, True, False)
        else:
            msg.is_logged = is_logged
            SESSION.delete(msg)
        SESSION.add(msg)
        SESSION.commit()
async def update_mode(id, mode):
    with INSERTION_LOCK:
        msg = SESSION.query(Database).get(id)
        if not msg:
            msg = Database(id, None, True, False)
        else:
            msg.upload_mode = mode
            SESSION.delete(msg)
        SESSION.add(msg)
        SESSION.commit()
async def update_thumb(id, thumb_id):
    with INSERTION_LOCK:
        msg = SESSION.query(Database).get(id)
        if not msg:
            msg = Database(id, thumb_id, True, False)
        else:
            msg.thumb_id = thumb_id
            SESSION.delete(msg)
        SESSION.add(msg)
        SESSION.commit()
async def del_user(id):
    with INSERTION_LOCK:
        msg = SESSION.query(Database).get(id)
        if msg:
            SESSION.delete(msg)
            SESSION.commit()
            return True
        else:
            return False
async def get_data(id):
    try:
        user_data = SESSION.query(Database).get(id)
        if not user_data:
            new_user = Database(id, None, True, False)
            SESSION.add(new_user)
            SESSION.commit()
            user_data = SESSION.query(Database).get(id)
        return user_data
    finally:
        SESSION.close()

       
    
class HashM:
    def __init__(self, uri, database_name):
        self._client = motor.motor_asyncio.AsyncIOMotorClient(uri)
        self.db = self._client[database_name]
        self.col = self.db.users

    def new_user(self, id):
        return dict(
            id=id,
            join_date=datetime.date.today().isoformat(),
            notif=True,
            ban_status=dict(
                is_banned=False,
                ban_duration=0,
                banned_on=datetime.date.max.isoformat(),
                ban_reason="",
            ),
        )

    async def add_user(self, id):
        user = self.new_user(id)
        await self.col.insert_one(user)

    async def is_user_exist(self, id):
        user = await self.col.find_one({"id": int(id)})
        return bool(user)

    async def total_users_count(self):
        count = await self.col.count_documents({})
        return count

    async def get_all_users(self):
        return self.col.find({})

    async def delete_user(self, user_id):
        await self.col.delete_many({"id": int(user_id)})

    async def remove_ban(self, id):
        ban_status = dict(
            is_banned=False,
            ban_duration=0,
            banned_on=datetime.date.max.isoformat(),
            ban_reason="",
        )
        await self.col.update_one({"id": id}, {"$set": {"ban_status": ban_status}})

    async def ban_user(self, user_id, ban_duration, ban_reason):
        ban_status = dict(
            is_banned=True,
            ban_duration=ban_duration,
            banned_on=datetime.date.today().isoformat(),
            ban_reason=ban_reason,
        )
        await self.col.update_one({"id": user_id}, {"$set": {"ban_status": ban_status}})

    async def get_ban_status(self, id):
        default = dict(
            is_banned=False,
            ban_duration=0,
            banned_on=datetime.date.max.isoformat(),
            ban_reason="",
        )
        user = await self.col.find_one({"id": int(id)})
        return user.get("ban_status", default)

    async def get_all_banned_users(self):
        return self.col.find({"ban_status.is_banned": True})

    async def set_notif(self, id, notif):
        await self.col.update_one({"id": id}, {"$set": {"notif": notif}})

    async def get_notif(self, id):
        user = await self.col.find_one({"id": int(id)})
        return user.get("notif", False)

    async def get_all_notif_user(self):
        return self.col.find({"notif": True})

    async def total_notif_users_count(self):
        count = await self.col.count_documents({"notif": True})
        return count
