import asyncio
import json
import logging
import secrets
import time
from contextlib import asynccontextmanager

import redis.asyncio as redis
from fastapi import Depends, FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import and_, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

import database
from auth import get_current_user
from config import (
    CONTROL_CHANNEL,
    CORS_ORIGINS,
    DEFAULT_HISTORY_LIMIT,
    MAX_HISTORY_LIMIT,
    MAX_MESSAGE_LENGTH,
    MESSAGE_RATE_LIMIT,
    MESSAGE_RATE_WINDOW_SECONDS,
    REDIS_CHANNEL,
    REDIS_URL,
    WS_TICKET_TTL_SECONDS,
)
from connection_manager import ConnectionManager
from database import get_db
from models import ChatRoom, ChatUser, Message
from schemas import MessageResponse, ParticipantResponse, RoomCreate, RoomResponse, WsTicketResponse
from user_events import run_consumer

logger = logging.getLogger(__name__)

redis_client = redis.from_url(REDIS_URL, decode_responses=True)
manager = ConnectionManager()


async def redis_listener():
    """
    Fan-out of messages published by any instance of this service to the WebSockets
    connected to *this* instance, plus control commands (closing a banned user's
    sockets). Reconnects if Redis goes away instead of leaving the instance deaf.
    """
    while True:
        try:
            pubsub = redis_client.pubsub()
            await pubsub.subscribe(REDIS_CHANNEL, CONTROL_CHANNEL)
            async for message in pubsub.listen():
                if message["type"] != "message":
                    continue
                data = json.loads(message["data"])
                if message["channel"] == CONTROL_CHANNEL:
                    if data.get("type") == "user_disabled":
                        await manager.disconnect_user(int(data["user_id"]))
                elif room_id := data.get("room_id"):
                    await manager.broadcast_to_room(room_id, message["data"])
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Redis listener failed, reconnecting in 2s")
            await asyncio.sleep(2)


@asynccontextmanager
async def lifespan(app: FastAPI):
    tasks = [
        asyncio.create_task(redis_listener()),
        asyncio.create_task(run_consumer(redis_client, database.SessionLocal)),
    ]
    yield
    for task in tasks:
        task.cancel()
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


async def get_chat_user(db: AsyncSession, user_id: int) -> ChatUser | None:
    return await db.get(ChatUser, user_id)


def to_participant(user_id: int, user: ChatUser | None) -> ParticipantResponse:
    if user is None:
        # Not synchronised yet (should only happen for a moment after sign-up).
        return ParticipantResponse(id=user_id, name=f"Użytkownik #{user_id}")
    if user.is_deleted:
        return ParticipantResponse(id=user_id, name="Usunięte konto")
    return ParticipantResponse(
        id=user_id,
        name=user.display_name or f"Użytkownik #{user_id}",
        avatar_url=user.avatar_url,
        trainer_username=user.trainer_username if user.accepts_new_conversations else None,
    )


async def get_current_participant(
    db: AsyncSession = Depends(get_db), user_id: int = Depends(get_current_user)
) -> int:
    """
    A valid token is not enough: the account may have been banned or deleted after
    the token was issued. The local user copy is kept current by the event stream.
    """
    user = await get_chat_user(db, user_id)
    if user is None or not user.can_chat:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is not allowed to chat")
    return user_id


@app.post("/rooms", response_model=RoomResponse)
async def create_or_get_room(room_data: RoomCreate, db: AsyncSession = Depends(get_db), current_user_id: int = Depends(get_current_participant)):
    if room_data.trainer_id == current_user_id:
        raise HTTPException(status_code=400, detail="You cannot start a conversation with yourself")
    trainer = await get_chat_user(db, room_data.trainer_id)
    if trainer is None or not (trainer.can_chat and trainer.accepts_new_conversations):
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
async def list_rooms(db: AsyncSession = Depends(get_db), current_user_id: int = Depends(get_current_participant)):
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

    partner_ids = {room.trainer_id if room.client_id == current_user_id else room.client_id for room in rooms}
    partners_stmt = select(ChatUser).where(ChatUser.user_id.in_(partner_ids))
    partners = {user.user_id: user for user in (await db.execute(partners_stmt)).scalars()}

    response = []
    for room in rooms:
        partner_id = room.trainer_id if room.client_id == current_user_id else room.client_id
        response.append(RoomResponse(
            id=room.id,
            client_id=room.client_id,
            trainer_id=room.trainer_id,
            created_at=room.created_at,
            last_message=last_messages.get(room.id),
            partner=to_participant(partner_id, partners.get(partner_id)),
        ))
    return response


@app.get("/rooms/{room_id}/messages", response_model=list[MessageResponse])
async def get_room_messages(
    room_id: int,
    limit: int = Query(DEFAULT_HISTORY_LIMIT, ge=1, le=MAX_HISTORY_LIMIT),
    before_id: int | None = Query(None, description="Return messages older than this id (pagination)"),
    db: AsyncSession = Depends(get_db),
    current_user_id: int = Depends(get_current_participant),
):
    if not await get_room_for_user(db, room_id, current_user_id):
        raise HTTPException(status_code=403, detail="Access denied to this room")

    stmt = select(Message).where(Message.room_id == room_id)
    if before_id is not None:
        stmt = stmt.where(Message.id < before_id)
    stmt = stmt.order_by(Message.id.desc()).limit(limit)
    messages = (await db.execute(stmt)).scalars().all()
    return list(reversed(messages))


def ws_ticket_key(ticket: str) -> str:
    return f"chat:ws_ticket:{ticket}"


@app.post("/ws-tickets", response_model=WsTicketResponse)
async def create_ws_ticket(current_user_id: int = Depends(get_current_participant)):
    """
    Browsers cannot send an Authorization header when opening a WebSocket, and a
    token in the URL ends up in proxy and access logs. Instead the page exchanges
    its token for a random ticket that is valid once, for a few seconds.
    """
    ticket = secrets.token_urlsafe(32)
    await redis_client.set(ws_ticket_key(ticket), current_user_id, ex=WS_TICKET_TTL_SECONDS)
    return WsTicketResponse(ticket=ticket, expires_in=WS_TICKET_TTL_SECONDS)


async def allow_message(user_id: int) -> bool:
    """
    Fixed-window counter in Redis. Counting per connection would let a user
    multiply the limit by opening more tabs, or by hitting several instances.
    """
    window = int(time.time() // MESSAGE_RATE_WINDOW_SECONDS)
    key = f"chat:rate:{user_id}:{window}"
    pipe = redis_client.pipeline()
    pipe.incr(key)
    pipe.expire(key, MESSAGE_RATE_WINDOW_SECONDS * 2)
    count, _ = await pipe.execute()
    return count <= MESSAGE_RATE_LIMIT


async def redeem_ws_ticket(ticket: str) -> int | None:
    # GETDEL is atomic: two connections racing with the same ticket cannot both win.
    user_id = await redis_client.getdel(ws_ticket_key(ticket))
    return int(user_id) if user_id is not None else None


@app.websocket("/ws/chat/{room_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: int, ticket: str = Query(...)):
    user_id = await redeem_ws_ticket(ticket)
    if user_id is None:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    # Short-lived sessions only: holding one DB connection for the whole lifetime
    # of a WebSocket would exhaust the connection pool with a few dozen idle chats.
    async with database.SessionLocal() as db:
        user = await get_chat_user(db, user_id)
        room = await get_room_for_user(db, room_id, user_id) if user and user.can_chat else None
    if not room:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await manager.connect(websocket, room_id, user_id)
    try:
        while True:
            content = (await websocket.receive_text()).strip()
            if not content:
                continue
            if len(content) > MAX_MESSAGE_LENGTH:
                await websocket.send_json({"error": f"Message longer than {MAX_MESSAGE_LENGTH} characters"})
                continue
            if not await allow_message(user_id):
                await websocket.send_json({"error": "Too many messages, slow down"})
                continue

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
        manager.disconnect(websocket, room_id, user_id)


@app.get("/health")
async def health_check():
    return {"status": "ok"}
