"""
Consumer of the `coachly.users.v1` stream: keeps the `chat_users` table in sync
with the main app.

Redis consumer groups give at-least-once delivery: an entry is acknowledged only
after it has been written to the database, so a crash replays it. Replays are
harmless because every write is guarded by the event id (version) - an event that
is not newer than what is stored changes nothing.
"""
import asyncio
import json
import logging
import os
import socket

from redis.exceptions import ResponseError
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from config import CONTROL_CHANNEL, USER_EVENTS_GROUP, USER_EVENTS_STREAM
from models import ChatUser

logger = logging.getLogger(__name__)

USER_UPDATED = 'user.updated'
USER_DELETED = 'user.deleted'

# Entries left pending by a crashed consumer are taken over after this long.
CLAIM_IDLE_MS = 60_000


class InvalidEvent(ValueError):
    """An entry that can never be processed (malformed or unknown type)."""


def consumer_name() -> str:
    return f"{socket.gethostname()}-{os.getpid()}"


def parse_entry(fields: dict) -> tuple[int, str, dict]:
    try:
        return int(fields['id']), fields['type'], json.loads(fields['payload'])
    except (KeyError, ValueError, TypeError) as exc:
        raise InvalidEvent(f"Malformed entry: {fields!r}") from exc


async def apply_user_event(db: AsyncSession, version: int, event_type: str, payload: dict) -> bool:
    """
    Upsert the user if the event is newer than the stored row.
    Returns True when the user can no longer chat (so live sessions must be closed).
    """
    if event_type == USER_UPDATED:
        values = {
            'display_name': payload.get('display_name') or '',
            'avatar_url': payload.get('avatar_url') or '',
            'trainer_username': payload.get('trainer_username'),
            'is_active': bool(payload['is_active']),
            'accepts_new_conversations': bool(payload['accepts_new_conversations']),
            'is_deleted': False,
        }
    elif event_type == USER_DELETED:
        values = {
            'display_name': '',
            'avatar_url': '',
            'trainer_username': None,
            'is_active': False,
            'accepts_new_conversations': False,
            'is_deleted': True,
        }
    else:
        raise InvalidEvent(f"Unknown event type {event_type!r}")

    stmt = insert(ChatUser).values(user_id=int(payload['user_id']), version=version, **values)
    stmt = stmt.on_conflict_do_update(
        index_elements=[ChatUser.user_id],
        set_={**values, 'version': stmt.excluded.version},
        where=ChatUser.version < stmt.excluded.version,
    )
    await db.execute(stmt)
    await db.commit()
    return not values['is_active']


async def ensure_group(redis_client) -> None:
    try:
        await redis_client.xgroup_create(USER_EVENTS_STREAM, USER_EVENTS_GROUP, id='0', mkstream=True)
    except ResponseError as exc:
        if 'BUSYGROUP' not in str(exc):
            raise


async def process_entries(redis_client, session_factory: async_sessionmaker, entries) -> None:
    for entry_id, fields in entries:
        try:
            version, event_type, payload = parse_entry(fields)
            async with session_factory() as db:
                revoked = await apply_user_event(db, version, event_type, payload)
            if revoked:
                await redis_client.publish(
                    CONTROL_CHANNEL, json.dumps({'type': 'user_disabled', 'user_id': int(payload['user_id'])})
                )
        except (InvalidEvent, KeyError) as exc:
            # Retrying cannot fix it; acknowledge so it does not block the group.
            logger.error("Dropping invalid user event %s: %s", entry_id, exc)
        except Exception:
            # Leave it pending: it is retried by this consumer or claimed by another.
            logger.exception("Failed to apply user event %s, will retry", entry_id)
            continue
        await redis_client.xack(USER_EVENTS_STREAM, USER_EVENTS_GROUP, entry_id)


async def consume_once(redis_client, session_factory, consumer: str, block_ms: int | None = 5000) -> int:
    """Process one batch: entries abandoned by dead consumers first, then new ones."""
    _next, claimed, *_ = await redis_client.xautoclaim(
        USER_EVENTS_STREAM, USER_EVENTS_GROUP, consumer, min_idle_time=CLAIM_IDLE_MS, start_id='0-0', count=100
    )
    if claimed:
        await process_entries(redis_client, session_factory, claimed)

    response = await redis_client.xreadgroup(
        USER_EVENTS_GROUP, consumer, {USER_EVENTS_STREAM: '>'}, count=100, block=block_ms
    )
    processed = len(claimed)
    for _stream, entries in response or []:
        await process_entries(redis_client, session_factory, entries)
        processed += len(entries)
    return processed


async def run_consumer(redis_client, session_factory) -> None:
    consumer = consumer_name()
    while True:
        try:
            await ensure_group(redis_client)
            while True:
                await consume_once(redis_client, session_factory, consumer)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("User event consumer failed, restarting in 2s")
            await asyncio.sleep(2)
