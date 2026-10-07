import asyncio
import json
import logging
import time
from contextlib import asynccontextmanager

import redis.asyncio as redis
from fastapi import Depends, FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import and_, or_, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

import database
from auth import get_current_user, verify_token
from config import (
    CORS_ORIGINS,
    DEFAULT_HISTORY_LIMIT,
    MAX_HISTORY_LIMIT,
    MAX_MESSAGE_LENGTH,
    MIN_SECONDS_BETWEEN_MESSAGES,
    REDIS_CHANNEL,
    REDIS_URL,
)
from connection_manager import ConnectionManager
from database import get_db
from models import ChatRoom, Message
from schemas import MessageResponse, RoomCreate, RoomResponse

logger = logging.getLogger(__name__)

redis_client = redis.from_url(REDIS_URL, decode_responses=True)
manager = ConnectionManager()


async def redis_listener():
    """
    Fan-out of chat messages published by any instance of this service to the
    WebSockets connected to *this* instance. Reconnects if Redis goes away
    instead of dying silently and leaving the instance deaf.
    """
    while True:
        try:
            pubsub = redis_client.pubsub()
            await pubsub.subscribe(REDIS_CHANNEL)
            async for message in pubsub.listen():
                if message["type"] != "message":
                    continue
                data = json.loads(message["data"])
                room_id = data.get("room_id")
                if room_id:
                    await manager.broadcast_to_room(room_id, message["data"])
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Redis listener failed, reconnecting in 2s")
            await asyncio.sleep(2)


@asynccontextmanager
async def lifespan(app: FastAPI):
    listener = asyncio.create_task(redis_listener())
    yield
    listener.cancel()
    await redis_client.aclose()


app = FastAPI(title="Live Chat Microservice", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)


async def get_room_for_user(db: AsyncSession, room_id: int, user_id: int) -> ChatRoom | None:
    """Returns the room only if the user is one of its two participants."""
    stmt = select(ChatRoom).where(
        ChatRoom.id == room_id,
        or_(ChatRoom.client_id == user_id, ChatRoom.trainer_id == user_id),
    )
    return (await db.execute(stmt)).scalars().first()


async def is_approved_trainer(db: AsyncSession, user_id: int) -> bool:
    # Users live in Django's table; both services share the same PostgreSQL database.
    result = await db.execute(
        text(
            "SELECT 1 FROM accounts_customuser "
            "WHERE id = :id AND status = 'APPROVED_TRAINER' AND is_active"
        ),
        {"id": user_id},
    )
    return result.first() is not None


@app.post("/rooms", response_model=RoomResponse)
async def create_or_get_room(room_data: RoomCreate, db: AsyncSession = Depends(get_db), current_user_id: int = Depends(get_current_user)):
    if room_data.trainer_id == current_user_id:
        raise HTTPException(status_code=400, detail="You cannot start a conversation with yourself")
    if not await is_approved_trainer(db, room_data.trainer_id):
        raise HTTPException(status_code=404, detail="Trainer not found")

    stmt = select(ChatRoom).where(
        and_(ChatRoom.client_id == current_user_id, ChatRoom.trainer_id == room_data.trainer_id)
    )
    room = (await db.execute(stmt)).scalars().first()
    if room:
        return room

    room = ChatRoom(client_id=current_user_id, trainer_id=room_data.trainer_id)
    db.add(room)
    try:
        await db.commit()
    except IntegrityError:
        # Two concurrent requests (e.g. a double click) - the unique constraint
        # let only one insert win, so return the room created by the other one.
        await db.rollback()
        return (await db.execute(stmt)).scalars().one()
    await db.refresh(room)
    return room


@app.get("/rooms", response_model=list[RoomResponse])
async def list_rooms(db: AsyncSession = Depends(get_db), current_user_id: int = Depends(get_current_user)):
    stmt = select(ChatRoom).where(
        or_(ChatRoom.client_id == current_user_id, ChatRoom.trainer_id == current_user_id)
    ).order_by(ChatRoom.created_at.desc())
    rooms = (await db.execute(stmt)).scalars().all()
    if not rooms:
        return []

    # One query for the latest message of every room (PostgreSQL DISTINCT ON)
    # instead of one query per room (N+1).
    last_messages_stmt = (
        select(Message)
        .where(Message.room_id.in_([room.id for room in rooms]))
        .distinct(Message.room_id)
        .order_by(Message.room_id, Message.created_at.desc(), Message.id.desc())
    )
    last_messages = {msg.room_id: msg for msg in (await db.execute(last_messages_stmt)).scalars()}

    return [
        RoomResponse(
            id=room.id,
            client_id=room.client_id,
            trainer_id=room.trainer_id,
            created_at=room.created_at,
            last_message=last_messages.get(room.id),
        )
        for room in rooms
    ]


@app.get("/rooms/{room_id}/messages", response_model=list[MessageResponse])
async def get_room_messages(
    room_id: int,
    limit: int = Query(DEFAULT_HISTORY_LIMIT, ge=1, le=MAX_HISTORY_LIMIT),
    before_id: int | None = Query(None, description="Return messages older than this id (pagination)"),
    db: AsyncSession = Depends(get_db),
    current_user_id: int = Depends(get_current_user),
):
    if not await get_room_for_user(db, room_id, current_user_id):
        raise HTTPException(status_code=403, detail="Access denied to this room")

    stmt = select(Message).where(Message.room_id == room_id)
    if before_id is not None:
        stmt = stmt.where(Message.id < before_id)
    stmt = stmt.order_by(Message.id.desc()).limit(limit)
    messages = (await db.execute(stmt)).scalars().all()
    return list(reversed(messages))


@app.websocket("/ws/chat/{room_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: int, token: str = Query(...)):
    try:
        user_id = verify_token(token)
    except HTTPException:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    # Short-lived sessions only: holding one DB connection for the whole lifetime
    # of a WebSocket would exhaust the connection pool with a few dozen idle chats.
    async with database.SessionLocal() as db:
        room = await get_room_for_user(db, room_id, user_id)
    if not room:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await manager.connect(websocket, room_id)
    last_message_at = 0.0
    try:
        while True:
            content = (await websocket.receive_text()).strip()
            if not content:
                continue
            if len(content) > MAX_MESSAGE_LENGTH:
                await websocket.send_json({"error": f"Message longer than {MAX_MESSAGE_LENGTH} characters"})
                continue
            now = time.monotonic()
            if now - last_message_at < MIN_SECONDS_BETWEEN_MESSAGES:
                await websocket.send_json({"error": "Too many messages, slow down"})
                continue
            last_message_at = now

            async with database.SessionLocal() as db:
                message = Message(room_id=room_id, sender_id=user_id, content=content)
                db.add(message)
                await db.commit()
                await db.refresh(message)

            await redis_client.publish(REDIS_CHANNEL, json.dumps({
                "id": message.id,
                "room_id": room_id,
                "sender_id": user_id,
                "content": content,
                "created_at": message.created_at.isoformat(),
            }))
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(websocket, room_id)


@app.get("/health")
async def health_check():
    return {"status": "ok"}
