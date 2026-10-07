import pytest
from starlette.websockets import WebSocketDisconnect

from tests.conftest import (
    APPROVED_TRAINER_ID,
    BANNED_CLIENT_ID,
    CLIENT_ID,
    OTHER_CLIENT_ID,
    PENDING_TRAINER_ID,
    auth,
    make_token,
)


def create_room(client, user_id=CLIENT_ID, trainer_id=APPROVED_TRAINER_ID):
    return client.post('/rooms', json={'trainer_id': trainer_id}, headers=auth(user_id))


class TestAuth:
    def test_requires_token(self, client):
        assert client.get('/rooms').status_code in (401, 403)

    def test_rejects_refresh_token(self, client):
        headers = {'Authorization': f'Bearer {make_token(CLIENT_ID, token_type="refresh")}'}
        assert client.get('/rooms', headers=headers).status_code == 401

    def test_rejects_token_signed_with_other_key(self, client):
        import jwt
        forged = jwt.encode({'user_id': CLIENT_ID, 'token_type': 'access'}, 'some-other-key', algorithm='HS256')
        assert client.get('/rooms', headers={'Authorization': f'Bearer {forged}'}).status_code == 401


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
        with client.websocket_connect(f'/ws/chat/{room_id}?token={make_token(CLIENT_ID)}') as ws:
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
        with client.websocket_connect(f'/ws/chat/{room_id}?token={make_token(APPROVED_TRAINER_ID)}') as trainer_ws, \
                client.websocket_connect(f'/ws/chat/{room_id}?token={make_token(CLIENT_ID)}') as client_ws:
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
            with client.websocket_connect(f'/ws/chat/{room_id}?token={make_token(OTHER_CLIENT_ID)}') as ws:
                ws.receive_text()

    def test_rejects_too_long_message(self, client):
        room_id = create_room(client).json()['id']
        with client.websocket_connect(f'/ws/chat/{room_id}?token={make_token(CLIENT_ID)}') as ws:
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
