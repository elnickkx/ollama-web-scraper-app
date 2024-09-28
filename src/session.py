
# -*- coding: utf-8 -*-
"""

@Filename : async DB connection
@created :  Sept 28 11:42 2020
@project: atlys-interview-assignment
@author : Nikkhil Butola
"""

import logging
from typing import AsyncGenerator
from config import SQLALCHEMY_DATABASE_URI, SQLALCHEMY_DATABASE_NAME

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
# from sqlalchemy import create_engine
from sqlalchemy.orm import (
    DeclarativeMeta,
    declarative_base,
)
from sqlalchemy.orm.session import sessionmaker
from sqlalchemy.schema import MetaData

naming_convention = {
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
}

_DBBase: DeclarativeMeta = declarative_base()
_DBBase.metadata = MetaData(naming_convention=naming_convention)  # defining the table naming as metadata

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
loggingFormat = "[%(filename)s: %(lineno)s- %(funcName)11s() ] %(asctime)s: %(name)s:%(levelname)s %(message)s"
logging.basicConfig(format=loggingFormat)

# database aysnc conn mod for PostgreSQL
DBEngine = create_async_engine(
    (
            "postgresql+asyncpg://"
            f"%s" % "postgres"
                    ":"
                    f"%s" % "postgres"
                            "@"
                            f"{SQLALCHEMY_DATABASE_URI}"
                            "/"
                            f"%s" % f"{SQLALCHEMY_DATABASE_NAME}"
    ),
    pool_pre_ping=True,
    pool_size=30,  ## sets the default pool size
)
DBSession = sessionmaker(DBEngine, autocommit=False, class_=AsyncSession, expire_on_commit=False)


# creating the SQLite database connection
# DATABASE_URL = "sqlite:///./event_management.db"
# DBEngine = create_engine(DATABASE_URL, connect_args={"check_same_thread": True})
# DBEngine = databases.Database(DATABASE_URL, force_rollback=True)


# build DB session dependency on query trigger
def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    _db = DBSession()
    try:
        yield _db

    finally:
       _db.close()


__all__ = ["DBSession", "get_async_session", "_DBBase", "DBEngine"]