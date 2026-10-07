import logging
from collections import defaultdict

from fastapi import WebSocket, status

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Tracks the WebSockets connected to this process, grouped by room and by user."""

    def __init__(self):
        # Sets, because the same user may have the chat open in several tabs.
        self.active_rooms: dict[int, set[WebSocket]] = defaultdict(set)
        self.user_sockets: dict[int, set[tuple[WebSocket, int]]] = defaultdict(set)

    async def connect(self, websocket: WebSocket, room_id: int, user_id: int) -> None:
        await websocket.accept()
        self.active_rooms[room_id].add(websocket)
        self.user_sockets[user_id].add((websocket, room_id))

    def disconnect(self, websocket: WebSocket, room_id: int, user_id: int) -> None:
        self._discard(self.active_rooms, room_id, websocket)
        self._discard(self.user_sockets, user_id, (websocket, room_id))

    @staticmethod
    def _discard(index: dict, key, value) -> None:
        values = index.get(key)
        if values is None:
            return
        values.discard(value)
        if not values:
            del index[key]

    async def broadcast_to_room(self, room_id: int, message: str) -> None:
        # Iterate over a copy: one broken connection must not stop delivery to the others.
        for websocket in list(self.active_rooms.get(room_id, ())):
            try:
                await websocket.send_text(message)
            except Exception:
                logger.info("Dropping dead WebSocket in room %s", room_id)
                self._discard(self.active_rooms, room_id, websocket)

    async def disconnect_user(self, user_id: int) -> None:
        """Close every socket of a user on this instance (e.g. after a ban)."""
        for websocket, room_id in list(self.user_sockets.get(user_id, ())):
            self.disconnect(websocket, room_id, user_id)
            try:
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            except Exception:
                pass
