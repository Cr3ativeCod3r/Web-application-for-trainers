from sqlalchemy import BigInteger, Boolean, Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from database import Base


class ChatRoom(Base):
    __tablename__ = "chat_rooms"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, index=True, nullable=False)
    trainer_id = Column(Integer, index=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    messages = relationship("Message", back_populates="room", cascade="all, delete")

    __table_args__ = (
        UniqueConstraint('client_id', 'trainer_id', name='uq_client_trainer_room'),
    )

class Message(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    room_id = Column(Integer, ForeignKey("chat_rooms.id", ondelete="CASCADE"), index=True, nullable=False)
    sender_id = Column(Integer, index=True, nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    room = relationship("ChatRoom", back_populates="messages")


class ChatUser(Base):
    """
    Local, read-only copy of the user data this service needs, fed by the
    `coachly.users.v1` event stream published by the main app. The main app's
    database is never queried directly.
    """
    __tablename__ = "chat_users"

    user_id = Column(Integer, primary_key=True, autoincrement=False)
    display_name = Column(String(255), nullable=False, default="")
    avatar_url = Column(Text, nullable=False, default="")
    trainer_username = Column(String(255), nullable=True)
    is_active = Column(Boolean, nullable=False, default=False)
    accepts_new_conversations = Column(Boolean, nullable=False, default=False)
    is_deleted = Column(Boolean, nullable=False, default=False)
    # Id of the last applied event; older or duplicated events are ignored.
    version = Column(BigInteger, nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    @property
    def can_chat(self) -> bool:
        return self.is_active and not self.is_deleted
