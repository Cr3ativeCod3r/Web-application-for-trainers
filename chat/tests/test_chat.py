import base64
import hashlib
import hmac
import json
import time
from datetime import timedelta

import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from starlette.websockets import WebSocketDisconnect

import main
from tests.conftest import (
    APPROVED_TRAINER_ID,
    BANNED_CLIENT_ID,
    CLIENT_ID,
    OTHER_CLIENT_ID,
    PENDING_TRAINER_ID,
    PUBLIC_KEY_PEM,
    auth,
    make_token,
    ws_url,
)


def bearer(token: str) -> dict:
    return {'Authorization': f'Bearer {token}'}


def _b64(data: dict) -> str:
    return base64.urlsafe_b64encode(json.dumps(data).encode()).rstrip(b'=').decode()


def create_room(client, user_id=CLIENT_ID, trainer_id=APPROVED_TRAINER_ID):
    return client.post('/rooms', json={'trainer_id': trainer_id}, headers=auth(user_id))


class TestAuth:
    def test_requires_token(self, client):
        assert client.get('/rooms').status_code in (401, 403)

    def test_accepts_valid_token(self, client):
        assert client.get('/rooms', headers=auth(CLIENT_ID)).status_code == 200

    def test_rejects_token_signed_with_other_key(self, client):
        other_key = ec.generate_private_key(ec.SECP256R1())
        forged = make_token(CLIENT_ID, key=other_key)
        assert client.get('/rooms', headers=bearer(forged)).status_code == 401

    def test_rejects_hs256_token_signed_with_the_public_key(self, client):
        """Algorithm confusion: the public key is public, it must not work as an HMAC secret."""
        # PyJWT itself refuses to use a PEM key as an HMAC secret, so build the token by hand.
        header = _b64({'alg': 'HS256', 'typ': 'JWT'})
        body = _b64({
            'iss': 'coachly-web', 'aud': 'coachly-chat', 'sub': str(CLIENT_ID),
            'iat': int(time.time()), 'exp': int(time.time()) + 60,
        })
        signature = base64.urlsafe_b64encode(
            hmac.new(PUBLIC_KEY_PEM.encode(), f'{header}.{body}'.encode(), hashlib.sha256).digest()
        ).rstrip(b'=').decode()
        forged = f'{header}.{body}.{signature}'
        assert client.get('/rooms', headers=bearer(forged)).status_code == 401

    def test_rejects_expired_token(self, client):
        expired = make_token(CLIENT_ID, lifetime=timedelta(seconds=-10))
        assert client.get('/rooms', headers=bearer(expired)).status_code == 401

    def test_rejects_token_for_another_audience(self, client):
        assert client.get('/rooms', headers=bearer(make_token(CLIENT_ID, aud='other-service'))).status_code == 401


class TestWebSocketTickets:
    def test_ticket_is_single_use(self, client):
        room_id = create_room(client).json()['id']
        url = ws_url(client, room_id, CLIENT_ID)
        with client.websocket_connect(url):
            pass
        with pytest.raises(WebSocketDisconnect), client.websocket_connect(url) as ws:
            ws.receive_text()

    def test_unknown_ticket_is_rejected(self, client):
        room_id = create_room(client).json()['id']
        with pytest.raises(WebSocketDisconnect), client.websocket_connect(f'/ws/chat/{room_id}?ticket=nope') as ws:
            ws.receive_text()

    def test_banned_user_cannot_get_ticket(self, client):
        assert client.post('/ws-tickets', headers=auth(BANNED_CLIENT_ID)).status_code == 403


class TestRooms:
    def test_create_room_is_idempotent(self, client):
        first = create_room(client)
        second = create_room(client)
        assert first.status_code == 200
        assert first.json()['id'] == second.json()['id']

    def test_cannot_open_room_with_non_trainer(self, client):
        assert create_room(client, trainer_id=PENDING_TRAINER_ID).status_code == 404
        assert create_room(client, trainer_id=OTHER_CLIENT_ID).status_code == 404

    def test_cannot_open_room_with_yourself(self, client):
        assert create_room(client, user_id=APPROVED_TRAINER_ID).status_code == 400

    def test_list_rooms_includes_last_message(self, client):
        room_id = create_room(client).json()['id']
        with client.websocket_connect(ws_url(client, room_id, CLIENT_ID)) as ws:
            ws.send_text('first')
            ws.receive_json()

        rooms = client.get('/rooms', headers=auth(APPROVED_TRAINER_ID)).json()
        assert len(rooms) == 1
        assert rooms[0]['last_message']['content'] == 'first'

    def test_list_rooms_includes_partner_display_data(self, client):
        create_room(client)

        client_view = client.get('/rooms', headers=auth(CLIENT_ID)).json()[0]['partner']
        trainer_view = client.get('/rooms', headers=auth(APPROVED_TRAINER_ID)).json()[0]['partner']

        assert client_view == {
            'id': APPROVED_TRAINER_ID, 'name': f'User {APPROVED_TRAINER_ID}',
            'avatar_url': '', 'trainer_username': f'trainer-{APPROVED_TRAINER_ID}',
        }
        assert trainer_view['id'] == CLIENT_ID
        assert trainer_view['trainer_username'] is None

    def test_outsider_cannot_read_messages(self, client):
        room_id = create_room(client).json()['id']
        response = client.get(f'/rooms/{room_id}/messages', headers=auth(OTHER_CLIENT_ID))
        assert response.status_code == 403


class TestWebSocket:
    def test_message_is_stored_and_delivered(self, client):
        room_id = create_room(client).json()['id']
        with client.websocket_connect(ws_url(client, room_id, APPROVED_TRAINER_ID)) as trainer_ws, \
                client.websocket_connect(ws_url(client, room_id, CLIENT_ID)) as client_ws:
            client_ws.send_text('Dzień dobry')
            received = trainer_ws.receive_json()

        assert received['content'] == 'Dzień dobry'
        assert received['sender_id'] == CLIENT_ID
        assert 'created_at' in received

        history = client.get(f'/rooms/{room_id}/messages', headers=auth(CLIENT_ID)).json()
        assert [m['content'] for m in history] == ['Dzień dobry']

    def test_outsider_cannot_connect(self, client):
        room_id = create_room(client).json()['id']
        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect(ws_url(client, room_id, OTHER_CLIENT_ID)) as ws:
                ws.receive_text()

    def test_rejects_too_long_message(self, client):
        room_id = create_room(client).json()['id']
        with client.websocket_connect(ws_url(client, room_id, CLIENT_ID)) as ws:
            ws.send_text('x' * 5000)
            assert 'error' in ws.receive_json()

        history = client.get(f'/rooms/{room_id}/messages', headers=auth(CLIENT_ID)).json()
        assert history == []


class TestDisabledAccounts:
    def test_banned_user_cannot_use_api_with_valid_token(self, client):
        assert client.get('/rooms', headers=auth(BANNED_CLIENT_ID)).status_code == 403

    def test_unknown_user_is_rejected(self, client):
        assert client.get('/rooms', headers=auth(999)).status_code == 403

    def test_cannot_open_room_with_banned_trainer(self, client):
        assert create_room(client, trainer_id=BANNED_CLIENT_ID).status_code == 404


class TestRateLimit:
    def test_limit_is_shared_between_connections_of_one_user(self, client, monkeypatch):
        monkeypatch.setattr(main, 'MESSAGE_RATE_LIMIT', 3)
        room_id = create_room(client).json()['id']

        with client.websocket_connect(ws_url(client, room_id, CLIENT_ID)) as tab_1, \
                client.websocket_connect(ws_url(client, room_id, CLIENT_ID)) as tab_2:
            for sender in (tab_1, tab_2, tab_1):
                sender.send_text('hi')
                # Every message is broadcast to all sockets in the room, the sender's included.
                tab_1.receive_json()
                tab_2.receive_json()
            tab_2.send_text('one too many')
            assert 'error' in tab_2.receive_json()

        history = client.get(f'/rooms/{room_id}/messages', headers=auth(CLIENT_ID)).json()
        assert len(history) == 3
