import asyncio
import os
import sys

import jwt
import pytest

# Configure the service before it is imported.
os.environ.setdefault('SECRET_KEY', 'test-only-insecure-secret-key')
os.environ.setdefault('DB_HOST', 'localhost')
os.environ['DB_NAME'] = os.environ.get('CHAT_TEST_DB_NAME', 'chat_test')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import fakeredis  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine  # noqa: E402
from sqlalchemy.pool import NullPool  # noqa: E402

import database  # noqa: E402
import main  # noqa: E402
from config import SECRET_KEY  # noqa: E402

# NullPool: TestClient runs the app in its own event loop, and asyncpg connections
# cannot be shared between loops.
test_engine = create_async_engine(database.SQLALCHEMY_DATABASE_URL, poolclass=NullPool)
database.engine = test_engine
database.SessionLocal = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)

APPROVED_TRAINER_ID = 10
PENDING_TRAINER_ID = 11
CLIENT_ID = 20
OTHER_CLIENT_ID = 21


async def _reset_schema():
    async with test_engine.begin() as conn:
        await conn.run_sync(database.Base.metadata.drop_all)
        await conn.run_sync(database.Base.metadata.create_all)
        # Minimal stand-in for Django's users table, which the service reads.
        await conn.execute(text("DROP TABLE IF EXISTS accounts_customuser"))
        await conn.execute(text(
            "CREATE TABLE accounts_customuser (id integer PRIMARY KEY, status varchar(30), is_active boolean)"
        ))
        await conn.execute(text(
            "INSERT INTO accounts_customuser VALUES "
            f"({APPROVED_TRAINER_ID}, 'APPROVED_TRAINER', true), "
            f"({PENDING_TRAINER_ID}, 'PENDING_APPLICATION', true), "
            f"({CLIENT_ID}, 'REGISTERED', true), "
            f"({OTHER_CLIENT_ID}, 'REGISTERED', true)"
        ))


@pytest.fixture(autouse=True)
def reset_db():
    asyncio.run(_reset_schema())


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(main, 'redis_client', fakeredis.aioredis.FakeRedis(decode_responses=True))
    with TestClient(main.app) as test_client:
        yield test_client


def make_token(user_id: int, token_type: str = 'access') -> str:
    return jwt.encode({'user_id': user_id, 'token_type': token_type}, SECRET_KEY, algorithm='HS256')


def auth(user_id: int) -> dict:
    return {'Authorization': f'Bearer {make_token(user_id)}'}
