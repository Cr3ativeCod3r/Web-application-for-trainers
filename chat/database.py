import os

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

from config import SQL_ECHO

# The chat service owns its database; it never connects to the main app's one.
SQLALCHEMY_DATABASE_URL = os.environ.get(
    'DATABASE_URL', 'postgresql+asyncpg://chat:chat@chat_db:5432/chat'
)

engine = create_async_engine(SQLALCHEMY_DATABASE_URL, echo=SQL_ECHO, pool_pre_ping=True)

SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

Base = declarative_base()


async def get_db():
    async with SessionLocal() as session:
        yield session
