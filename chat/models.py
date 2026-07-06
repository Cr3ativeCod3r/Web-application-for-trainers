from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, UniqueConstraint
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
