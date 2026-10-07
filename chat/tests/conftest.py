import asyncio
import os
import sys

import jwt
import pytest

# Configure the service before it is imported.
os.environ.setdefault('SECRET_KEY', 'test-only-insecure-secret-key-not-for-production-use')
os.environ.setdefault('DB_HOST', 'localhost')
os.environ['DB_NAME'] = os.environ.get('CHAT_TEST_DB_NAME', 'chat_test')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import fakeredis  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine  # noqa: E402
from sqlalchemy.pool import NullPool  # noqa: E402

import database  # noqa: E402
import main  # noqa: E402
from config import SECRET_KEY  # noqa: E402
from models import ChatUser  # noqa: E402

# NullPool: TestClient runs the app in its own event loop, and asyncpg connections
# cannot be shared between loops.
test_engine = create_async_engine(database.SQLALCHEMY_DATABASE_URL, poolclass=NullPool)
database.engine = test_engine
database.SessionLocal = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)

APPROVED_TRAINER_ID = 10
PENDING_TRAINER_ID = 11
CLIENT_ID = 20
OTHER_CLIENT_ID = 21
BANNED_CLIENT_ID = 22


def chat_user(user_id: int, *, trainer: bool = False, active: bool = True, version: int = 1) -> ChatUser:
    return ChatUser(
        user_id=user_id,
        display_name=f"User {user_id}",
        avatar_url="",
        trainer_username=f"trainer-{user_id}" if trainer else None,
        is_active=active,
        accepts_new_conversations=trainer and active,
        is_deleted=False,
        version=version,
    )


async def _reset_schema():
    async with test_engine.begin() as conn:
        await conn.run_sync(database.Base.metadata.drop_all)
        await conn.run_sync(database.Base.metadata.create_all)
    async with database.SessionLocal() as db:
        db.add_all([
            chat_user(APPROVED_TRAINER_ID, trainer=True),
            chat_user(PENDING_TRAINER_ID),
            chat_user(CLIENT_ID),
            chat_user(OTHER_CLIENT_ID),
            chat_user(BANNED_CLIENT_ID, active=False),
        ])
        await db.commit()


@pytest.fixture(autouse=True)
def reset_db():
    asyncio.run(_reset_schema())


async def _idle(*_args):
    await asyncio.Event().wait()


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(main, 'redis_client', fakeredis.aioredis.FakeRedis(decode_responses=True))
    # The stream consumer is exercised directly in test_user_events.py.
    monkeypatch.setattr(main, 'run_consumer', _idle)
    with TestClient(main.app) as test_client:
        yield test_client


def make_token(user_id: int, token_type: str = 'access') -> str:
    return jwt.encode({'user_id': user_id, 'token_type': token_type}, SECRET_KEY, algorithm='HS256')


def auth(user_id: int) -> dict:
    return {'Authorization': f'Bearer {make_token(user_id)}'}
