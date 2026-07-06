import os
from typing import Dict, List
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException, status, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, and_
import jwt
from jwt.exceptions import InvalidTokenError
import json
import redis.asyncio as redis
import asyncio

from database import get_db, init_db
from models import Message, ChatRoom
from schemas import RoomResponse, RoomCreate, MessageResponse

app = FastAPI(title="Live Chat Microservice")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://0.0.0.0:8000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-(=+dp(si1)ucdw(o@k9$@9@(hkvk-*52!jpo@4nydxyz4rgg@b')
REDIS_URL = os.environ.get('REDIS_URL', 'redis://redis:6379/0')

redis_client = redis.from_url(REDIS_URL, decode_responses=True)

class ConnectionManager:
    def __init__(self):
        # Maps room_id to a dict of user_id -> WebSocket
        self.active_rooms: Dict[int, Dict[int, WebSocket]] = {}

    async def connect(self, websocket: WebSocket, room_id: int, user_id: int):
        await websocket.accept()
        if room_id not in self.active_rooms:
            self.active_rooms[room_id] = {}
        self.active_rooms[room_id][user_id] = websocket

    def disconnect(self, room_id: int, user_id: int):
        if room_id in self.active_rooms and user_id in self.active_rooms[room_id]:
            del self.active_rooms[room_id][user_id]
            if not self.active_rooms[room_id]:
                del self.active_rooms[room_id]

    async def broadcast_to_room(self, room_id: int, message: str):
        if room_id in self.active_rooms:
            for connection in self.active_rooms[room_id].values():
                await connection.send_text(message)

manager = ConnectionManager()
security = HTTPBearer()

def verify_token(token: str) -> int:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        user_id = payload.get("user_id")
        if user_id is None:
            raise InvalidTokenError()
        return int(user_id)
    except InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> int:
    return verify_token(credentials.credentials)

@app.on_event("startup")
async def on_startup():
    asyncio.create_task(redis_listener())

async def redis_listener():
    pubsub = redis_client.pubsub()
    await pubsub.subscribe("chat_messages")
    async for message in pubsub.listen():
        if message["type"] == "message":
            data = json.loads(message["data"])
            room_id = data.get("room_id")
            if room_id:
                await manager.broadcast_to_room(room_id, message["data"])

@app.post("/rooms", response_model=RoomResponse)
async def create_or_get_room(room_data: RoomCreate, db: AsyncSession = Depends(get_db), current_user_id: int = Depends(get_current_user)):
    # Check if room already exists
    stmt = select(ChatRoom).where(
        and_(ChatRoom.client_id == current_user_id, ChatRoom.trainer_id == room_data.trainer_id)
    )
    result = await db.execute(stmt)
    room = result.scalars().first()
    
    if not room:
        room = ChatRoom(client_id=current_user_id, trainer_id=room_data.trainer_id)
        db.add(room)
        await db.commit()
        await db.refresh(room)
        
    return room

@app.get("/rooms", response_model=List[RoomResponse])
async def list_rooms(db: AsyncSession = Depends(get_db), current_user_id: int = Depends(get_current_user)):
    stmt = select(ChatRoom).where(
        or_(ChatRoom.client_id == current_user_id, ChatRoom.trainer_id == current_user_id)
    ).order_by(ChatRoom.created_at.desc())

    result = await db.execute(stmt)
    rooms = result.scalars().all()

    # Attach last message to each room
    response = []
    for room in rooms:
        last_msg_stmt = (
            select(Message)
            .where(Message.room_id == room.id)
            .order_by(Message.created_at.desc())
            .limit(1)
        )
        last_msg_result = await db.execute(last_msg_stmt)
        last_msg = last_msg_result.scalars().first()
        room_dict = {
            "id": room.id,
            "client_id": room.client_id,
            "trainer_id": room.trainer_id,
            "created_at": room.created_at,
            "last_message": last_msg,
        }
        response.append(room_dict)

    return response

@app.get("/rooms/{room_id}/messages", response_model=List[MessageResponse])
async def get_room_messages(room_id: int, db: AsyncSession = Depends(get_db), current_user_id: int = Depends(get_current_user)):
    # Verify access to room
    stmt = select(ChatRoom).where(ChatRoom.id == room_id)
    result = await db.execute(stmt)
    room = result.scalars().first()
    
    if not room or (room.client_id != current_user_id and room.trainer_id != current_user_id):
        raise HTTPException(status_code=403, detail="Access denied to this room")
        
    msg_stmt = select(Message).where(Message.room_id == room_id).order_by(Message.created_at.asc())
    msg_result = await db.execute(msg_stmt)
    return msg_result.scalars().all()

@app.websocket("/ws/chat/{room_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: int, token: str = Query(...), db: AsyncSession = Depends(get_db)):
    try:
        user_id = verify_token(token)
    except HTTPException:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    # Verify access to room
    stmt = select(ChatRoom).where(ChatRoom.id == room_id)
    result = await db.execute(stmt)
    room = result.scalars().first()
    
    if not room or (room.client_id != user_id and room.trainer_id != user_id):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await manager.connect(websocket, room_id, user_id)
    
    try:
        while True:
            data = await websocket.receive_text()
            # Save to DB
            new_message = Message(room_id=room_id, sender_id=user_id, content=data)
            db.add(new_message)
            await db.commit()
            
            # Publish to Redis
            msg_payload = json.dumps({
                "room_id": room_id,
                "sender_id": user_id,
                "content": data
            })
            await redis_client.publish("chat_messages", msg_payload)
            
    except WebSocketDisconnect:
        manager.disconnect(room_id, user_id)

@app.get("/health")
async def health_check():
    return {"status": "ok"}
