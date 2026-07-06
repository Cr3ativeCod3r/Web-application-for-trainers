from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class MessageBase(BaseModel):
    content: str

class MessageCreate(MessageBase):
    pass

class MessageResponse(MessageBase):
    id: int
    room_id: int
    sender_id: int
    created_at: datetime

    class Config:
        from_attributes = True

class RoomCreate(BaseModel):
    trainer_id: int

class RoomResponse(BaseModel):
    id: int
    client_id: int
    trainer_id: int
    created_at: datetime
    last_message: Optional[MessageResponse] = None

    class Config:
        from_attributes = True
