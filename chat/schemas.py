from datetime import datetime

from pydantic import BaseModel, ConfigDict


class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    room_id: int
    sender_id: int
    content: str
    created_at: datetime


class RoomCreate(BaseModel):
    trainer_id: int


class RoomResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    client_id: int
    trainer_id: int
    created_at: datetime
    last_message: MessageResponse | None = None
