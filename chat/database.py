import os

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

from config import SQL_ECHO

DB_USER = os.environ.get('DB_USER', 'trainuser')
DB_PASS = os.environ.get('DB_PASS', 'trainpass')
DB_HOST = os.environ.get('DB_HOST', 'db')
DB_PORT = os.environ.get('DB_PORT', '5432')
DB_NAME = os.environ.get('DB_NAME', 'trainapp')

SQLALCHEMY_DATABASE_URL = f"postgresql+asyncpg://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

engine = create_async_engine(SQLALCHEMY_DATABASE_URL, echo=SQL_ECHO, pool_pre_ping=True)

SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

Base = declarative_base()


async def get_db():
    async with SessionLocal() as session:
        yield session
