
# -*- coding: utf-8 -*-
"""

@Filename : db app interface
@created :  Sept 28 11:42 2020
@project: atlys-interview-assignment
@author : Nikkhil Butola
"""

import asyncio
import json
import logging
from datetime import datetime
import typing
from fastapi import Depends, HTTPException
import uuid

from sqlalchemy import (
    Column,
    ForeignKey,
    Integer,
    String,
    Boolean,
    DateTime,
    Enum,
    update,
    select,
    VARCHAR,
    Text,
    DECIMAL,
    and_,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import (
    relationship,
    Session,
)
import enum
import traceback
from secure_handling import get_password_hash
from session import DBSession, get_async_session, _DBBase, DBEngine


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
loggingFormat = "[%(filename)s: %(lineno)s- %(funcName)11s() ] %(asctime)s: %(name)s:%(levelname)s %(message)s"
logging.basicConfig(format=loggingFormat)


class EventStatus(enum.Enum):
    opened = "OPENED"
    closed = "CLOSED"
    past = "PAST"
    canceled = "CANCELLED"
    rescheduled = "RESCHEDULED"


class UserTable(_DBBase):
    __tablename__ = "users"

    user_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid1(), index=True)
    username = Column(String(255), nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String(256), nullable=False)
    first_name = Column(String(150))
    last_name = Column(String(150))
    is_active = Column(Boolean, default=False)
    is_admin = Column(Boolean, default=False)
    # parent_id = Column(UUID(as_uuid=True), ForeignKey(id))  ## confirm the syntax

    # foreign relationship mapping
    events = relationship("ScrapeEventTable", back_populates="user")

    def serialize(self):
        return {"name": self.username, "id": str(self.user_id), "type": self.email}

    @classmethod
    def validate_user(cls, *, user_id):
        if not user_id:
            return

        return user_id

    @classmethod
    async def get_user_by_email(cls, *, email_addr: str):
        try:
            async with DBSession() as session:
                async with session.begin():
                    query = select(cls).where(cls.email == email_addr, cls.is_active==True)
                    query = await session.execute(query)
                    user = query.one()[0]

                await session.close()

        except Exception:
            logger.error(traceback.format_exc())
            return None

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        return user

    @classmethod
    async def create(cls, *, params, _db: Session = Depends(get_async_session)):
        if not params.email_address:
            return None

        # check whether user with email addr exists
        if params.email_address:
            if _user := await cls.get_user_by_email(email_addr=params.email_address):
                return _us

        try:
            # or create a new user with email address
            hashed_password = get_password_hash(params.password)
            user = cls(
                username=params.username,
                email=params.email_address,
                hashed_password=hashed_password,
                first_name=params.first_name,
                last_name=params.last_name,
                is_admin=params.is_admin,
                is_active=True,
            )

            async with DBSession() as session:
                async with session.begin():
                    _ = session.add(user)

                await session.commit()
                session.refresh(user)
                session.close()

        except Exception:
            logger.error(traceback.format_exc())
            raise Exception

        else:
            return user

    @classmethod
    async def update_metadata(cls, *, user_id, **kwargs):
        try:
            async with DBSession() as session:
                async with session.begin():
                    query = update(cls).where(cls.user_id == user_id).values(**kwargs)
                    await session.execute(query)

                await session.commit()
                session.refresh(cls)
                await session.close()

        except Exception:
            logger.error(traceback.format_exc())
            return "no user found"

        else:
            return "updated successfully ..."

    @classmethod
    async def get_user(cls, *, user_id: int):
        try:
            async with DBSession() as session:
                async with session.begin():
                    query = select(cls).where(cls.user_id == user_id)
                    query = await session.execute(query)
                    user = query.one()[0]

                await session.close()

        except Exception:
            logger.error(traceback.format_exc())
            return None

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        return user


class ScrapeEventTable(_DBBase):
    __tablename__ = "scrape_events"

    event_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid1(), index=True)
    event_name = Column(String(255), nullable=False)
    website_uri = Column(String, unique=True, index=True, nullable=False)
    file_blob_path = Column(String(255), nullable=False)
    # to interlink the rescheduled or overridden event job, need to try implementation by PK
    parent_id = Column(UUID(as_uuid=True), index=True, nullable=True)
    start_date = Column(DateTime, default=datetime.utcnow)
    end_date = Column(DateTime, onupdate=datetime.utcnow, nullable=True)
    durations = Column(Integer, nullable=True)
    # status = Column(Enum(EventStatus), nullable=False)
    status = Column(String, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    recipient_delivery = Column(Boolean, default=False, nullable=False)
    counted_products = Column(Integer, default=0,  nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"))
    event_metadata = Column(JSONB, nullable=True)

    # foreignKey relations
    user = relationship("UserTable", back_populates="events")

    def serialize(self):
        return {"name": self.event_name, "id": str(self.event_id), "current_status": self.status, "website_uri": self.website_uri, "start_date": str(self.start_date), "end_date": str(self.end_date), "counted_products": self.counted_products}

    @classmethod
    async def create(cls, *, params, _db: Session = Depends(get_async_session)):
        _parent_id = None
        if not params.website_uri:
            return None

        _event_metadata = cls(
            event_name=params.event_name,
            website_uri=params.website_uri,
            start_date=params.start_date,
            status=params.status,
            is_active=True,
            # user_id=params.user_id,
            event_metadata={
                "page_offset": params.pages,
                "proxy_string": params.proxy_string,
            }
        )

        try:
            async with DBSession() as session:
                async with session.begin():
                    _ = session.add(_event_metadata)

                await session.commit()
                await session.refresh(_event_metadata)
                await session.close()

        except Exception:
            logger.error(traceback.format_exc())
            return None

        return _event_metadata

    @classmethod
    async def get_event_details(cls, *, event_id: str):
        try:
            async with DBSession() as session:
                async with session.begin():
                    query = select(cls).where(cls.event_id == event_id)
                    query = await session.execute(query)
                    _response = query.one()[0]

                await session.commit()
                session.refresh(cls)
                await session.close()

        except Exception:
            logger.error(traceback.format_exc())
            return None

        else:
            return _response

    @classmethod
    async def get_event_details_by_uri(cls, *, target_uri: str):
        try:
            async with DBSession() as session:
                async with session.begin():
                    query = select(cls).where(cls.website_uri == target_uri).order_by(cls.start_date.desc())
                    query = await session.execute(query)
                    _response = query.all()[0]

                await session.commit()
                session.refresh(cls)
                await session.close()

        except Exception:
            logger.error(traceback.format_exc())
            return None

        else:
            return _response[0]

    @classmethod
    async def update_event_metadata(cls, *, event_id, **kwargs):
        try:
            async with DBSession() as session:
                async with session.begin():
                    query = update(cls).where(cls.event_id == event_id).values(**kwargs)
                    await session.execute(query)

                await session.commit()
                logger.info(f"Successfully updated the Event metadata for {event_id = } ...")
                return True

        except Exception:
            logger.error(traceback.format_exc())
            return None

    @classmethod
    async def fetch_all_available_events(cls,*, user_id: int):
        try:
            async with DBSession() as session:
                async with session.begin():
                    query = select(cls).where(cls.is_active == True, cls.user_id == user_id).order_by(cls.event_id)
                    query = await session.execute(query)
                    _response = query.all()

                await session.commit()
                logger.info(f"Successfully fetched all the active events existing in Database ...")
                return _response

        except Exception:
            logger.error(traceback.format_exc())
            return None


class TransactionTable(_DBBase):
    __tablename__ = "transactions"

    transaction_id = Column(UUID(as_uuid=True), primary_key=True, index=True)
    transaction_date = Column(DateTime, default=datetime.utcnow)
    column_name = Column(String(255), nullable=False)
    existing_value = Column(String(255), nullable=False)
    updated_value = Column(String(255), nullable=False)
    blob_filename = Column(String(255), nullable=False)

    # foreign key referencin'
    event_id = Column(UUID(as_uuid=True), ForeignKey("scrape_events.event_id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)

    def serialize(self):
        return {"transaction_id": self.transaction_id, "blob_filename": self.blob_filename, "event_id": self.event_id, "user_id": self.user_id, }

    @classmethod
    async def perform_event_transaction(cls, *, column_name: str, existing_value: str, updated_value: str, event_id: str, user_id: str, blob_filename: str, _db: Session = Depends(get_async_session)):
        if not event_id:
            return "Event id associated with uri scraping doesn't exists ..."

        try:
            _tranx_metadata = cls(
                transaction_id=uuid.uuid1(),
                column_name=column_name,
                existing_value=existing_value,
                updated_value=updated_value,
                event_id=event_id,
                user_id=user_id,
                blob_filename=blob_filename,
                )

            async with DBSession() as session:
                async with session.begin():
                    _ = session.add(_tranx_metadata)

                await session.commit()
                await session.refresh(_tranx_metadata)
                await session.close()

        except Exception:
            logger.error(traceback.format_exc())
            return None

        else:
            return _tranx_metadata.transaction_id

    @classmethod
    async def update_transaction_metadata(cls, *, transaction_id: str, **kwargs):
        try:
            async with DBSession() as session:
                async with session.begin():
                    query = update(cls).where(cls.transaction_id == transaction_id).values(**kwargs)
                    await session.execute(query)

                await session.commit()
                session.refresh(cls)
                await session.close()

                return True

        except Exception:
            logger.error(traceback.format_exc())
            return None

    @classmethod
    async def fetch_tranx_metadata_by_event_id(cls, /, event_id: str, blob_filename: str):
        """

        :param event_id:
        :param blob_filename:
        :return:
        """

        try:
            async with DBSession() as session:
                async with session.begin():
                    query = select(cls).where(
                        and_(
                            cls.event_id == event_id,
                            cls.blob_filename == blob_filename,
                        )

                    ).order_by(cls.transaction_date.desc())
                    query = await session.execute(query)
                    _response = query.all()

                await session.commit()
                session.refresh(cls)
                await session.close()

        except Exception:
            logger.error(traceback.format_exc())
            return None

        else:
            return _response


def run():
    res = asyncio.run(UserTable.validate_user(user_id=1))
    return res
