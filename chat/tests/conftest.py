import asyncio
import os
import sys
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec

# A throwaway key pair: tests play the role of the main app and sign tokens.
PRIVATE_KEY = ec.generate_private_key(ec.SECP256R1())
PUBLIC_KEY_PEM = PRIVATE_KEY.public_key().public_bytes(
    serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
).decode()

# Configure the service before it is imported.
os.environ['JWT_PUBLIC_KEY'] = PUBLIC_KEY_PEM
os.environ['DATABASE_URL'] = os.environ.get(
    'CHAT_TEST_DATABASE_URL', 'postgresql+asyncpg://trainuser:trainpass@localhost:5432/chat_test'
)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import fakeredis  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine  # noqa: E402
from sqlalchemy.pool import NullPool  # noqa: E402

import database  # noqa: E402
import main  # noqa: E402
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


def make_token(user_id: int, *, key=PRIVATE_KEY, algorithm='ES256', lifetime=timedelta(minutes=5), **overrides) -> str:
    now = datetime.now(UTC)
    claims = {
        'iss': 'coachly-web',
        'aud': 'coachly-chat',
        'sub': str(user_id),
        'iat': now,
        'exp': now + lifetime,
        **overrides,
    }
    return jwt.encode(claims, key, algorithm=algorithm)


def auth(user_id: int) -> dict:
    return {'Authorization': f'Bearer {make_token(user_id)}'}


def ws_url(client, room_id: int, user_id: int) -> str:
    """What the browser does: exchange the token for a one-time ticket, then connect."""
    response = client.post('/ws-tickets', headers=auth(user_id))
    assert response.status_code == 200, response.text
    return f"/ws/chat/{room_id}?ticket={response.json()['ticket']}"
