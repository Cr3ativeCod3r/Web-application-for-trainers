import logging
from collections import defaultdict

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Tracks the WebSockets connected to this process, grouped by room."""

    def __init__(self):
        # A set per room: the same user may have the chat open in several tabs.
        self.active_rooms: dict[int, set[WebSocket]] = defaultdict(set)

    async def connect(self, websocket: WebSocket, room_id: int) -> None:
        await websocket.accept()
        self.active_rooms[room_id].add(websocket)

    def disconnect(self, websocket: WebSocket, room_id: int) -> None:
        connections = self.active_rooms.get(room_id)
        if connections is None:
            return
        connections.discard(websocket)
        if not connections:
            del self.active_rooms[room_id]

    async def broadcast_to_room(self, room_id: int, message: str) -> None:
        # Iterate over a copy: a dead socket is removed while we loop, and one
        # broken connection must not stop delivery to the others.
        for websocket in list(self.active_rooms.get(room_id, ())):
            try:
                await websocket.send_text(message)
            except Exception:
                logger.info("Dropping dead WebSocket in room %s", room_id)
                self.disconnect(websocket, room_id)
