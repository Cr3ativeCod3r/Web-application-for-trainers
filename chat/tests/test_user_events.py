import asyncio
import json

import fakeredis
import pytest
from starlette.websockets import WebSocketDisconnect

import database
import main
from config import CONTROL_CHANNEL, USER_EVENTS_GROUP, USER_EVENTS_STREAM
from models import ChatUser
from tests.conftest import APPROVED_TRAINER_ID, CLIENT_ID, make_token
from user_events import consume_once, ensure_group

NEW_USER_ID = 50


def updated(version, user_id=NEW_USER_ID, **overrides):
    payload = {
        'schema_version': 1,
        'user_id': user_id,
        'display_name': 'Anna',
        'avatar_url': '',
        'trainer_username': 'anna',
        'is_active': True,
        'accepts_new_conversations': True,
        **overrides,
    }
    return {'id': str(version), 'type': 'user.updated', 'aggregate_id': str(user_id), 'payload': json.dumps(payload)}


def deleted(version, user_id=NEW_USER_ID):
    payload = {'schema_version': 1, 'user_id': user_id}
    return {'id': str(version), 'type': 'user.deleted', 'aggregate_id': str(user_id), 'payload': json.dumps(payload)}


async def deliver(*entries):
    """Publish entries to a fresh fake stream and let one consumer process them."""
    redis_client = fakeredis.aioredis.FakeRedis(decode_responses=True)
    pubsub = redis_client.pubsub()
    await pubsub.subscribe(CONTROL_CHANNEL)
    await pubsub.get_message(timeout=0.1)  # subscribe confirmation

    await ensure_group(redis_client)
    for fields in entries:
        await redis_client.xadd(USER_EVENTS_STREAM, fields)
    await consume_once(redis_client, database.SessionLocal, 'test-consumer', block_ms=None)

    pending = await redis_client.xpending(USER_EVENTS_STREAM, USER_EVENTS_GROUP)
    controls = []
    while message := await pubsub.get_message(timeout=0.1):
        controls.append(json.loads(message['data']))
    return pending['pending'], controls


async def load(user_id):
    async with database.SessionLocal() as db:
        return await db.get(ChatUser, user_id)


def run(coro):
    return asyncio.run(coro)


class TestApplyingEvents:
    def test_creates_user_and_acknowledges(self):
        pending, _ = run(deliver(updated(5)))

        user = run(load(NEW_USER_ID))
        assert user.display_name == 'Anna'
        assert user.accepts_new_conversations is True
        assert user.version == 5
        assert pending == 0

    def test_out_of_order_event_is_ignored(self):
        run(deliver(updated(7, display_name='New name'), updated(6, display_name='Old name')))
        user = run(load(NEW_USER_ID))
        assert user.display_name == 'New name'
        assert user.version == 7

    def test_redelivered_event_is_idempotent(self):
        run(deliver(updated(5), updated(5, display_name='Replay')))
        assert run(load(NEW_USER_ID)).display_name == 'Anna'

    def test_delete_turns_user_into_tombstone(self):
        run(deliver(updated(5), deleted(6)))
        user = run(load(NEW_USER_ID))
        assert user.is_deleted is True
        assert user.can_chat is False
        assert user.display_name == ''

    def test_deactivation_tells_instances_to_close_sockets(self):
        _, controls = run(deliver(updated(5, is_active=False, accepts_new_conversations=False)))
        assert controls == [{'type': 'user_disabled', 'user_id': NEW_USER_ID}]

    def test_invalid_entry_is_dropped_without_blocking_the_group(self):
        pending, _ = run(deliver({'id': 'x', 'type': 'user.updated', 'payload': '{}'}, updated(5)))
        assert pending == 0
        assert run(load(NEW_USER_ID)) is not None


class TestKickingDisabledUsers:
    def test_ban_closes_open_websocket(self, client):
        room_id = client.post('/rooms', json={'trainer_id': APPROVED_TRAINER_ID},
                              headers={'Authorization': f'Bearer {make_token(CLIENT_ID)}'}).json()['id']

        with client.websocket_connect(f'/ws/chat/{room_id}?token={make_token(CLIENT_ID)}') as ws:
            client.portal.call(
                main.redis_client.publish, CONTROL_CHANNEL, json.dumps({'type': 'user_disabled', 'user_id': CLIENT_ID})
            )
            with pytest.raises(WebSocketDisconnect):
                ws.receive_text()
