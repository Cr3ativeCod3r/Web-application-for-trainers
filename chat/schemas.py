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


class ParticipantResponse(BaseModel):
    """Public display data of the other person in a conversation."""
    id: int
    name: str
    avatar_url: str = ""
    trainer_username: str | None = None


class RoomResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    client_id: int
    trainer_id: int
    created_at: datetime
    last_message: MessageResponse | None = None
    partner: ParticipantResponse | None = None


class WsTicketResponse(BaseModel):
    ticket: str
    expires_in: int
