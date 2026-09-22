"""Persistent private chats, independent of roulette matches and archives."""
from datetime import datetime
from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, Text, UniqueConstraint, CheckConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column
from app.models import Base


class DirectChat(Base):
    __tablename__ = 'direct_chats'
    __table_args__ = (UniqueConstraint('user_one', 'user_two'), CheckConstraint('user_one < user_two'))
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_one: Mapped[int] = mapped_column(BigInteger, ForeignKey('users.telegram_id', ondelete='CASCADE'), index=True)
    user_two: Mapped[int] = mapped_column(BigInteger, ForeignKey('users.telegram_id', ondelete='CASCADE'), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    revision: Mapped[int] = mapped_column(BigInteger, default=0)


class DirectMessage(Base):
    __tablename__ = 'direct_messages'
    __table_args__ = (Index('ix_direct_message_chat_revision', 'chat_id', 'revision'), Index('ix_direct_message_chat_id', 'chat_id', 'id'))
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    chat_id: Mapped[int] = mapped_column(ForeignKey('direct_chats.id', ondelete='CASCADE'), index=True)
    sender_id: Mapped[int] = mapped_column(BigInteger, ForeignKey('users.telegram_id', ondelete='CASCADE'))
    text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revision: Mapped[int] = mapped_column(BigInteger)
    is_edited: Mapped[bool] = mapped_column(Boolean, default=False)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)

class DirectMessageDeletion(Base):
    __tablename__ = 'direct_message_deletions'
    __table_args__ = (UniqueConstraint('message_id', 'user_id'),)
    message_id: Mapped[int] = mapped_column(ForeignKey('direct_messages.id', ondelete='CASCADE'), primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey('users.telegram_id', ondelete='CASCADE'), primary_key=True)
    deleted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class DirectRead(Base):
    __tablename__ = 'direct_chat_reads'
    chat_id: Mapped[int] = mapped_column(ForeignKey('direct_chats.id', ondelete='CASCADE'), primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey('users.telegram_id', ondelete='CASCADE'), primary_key=True)
    last_message_id: Mapped[int] = mapped_column(Integer, default=0)


class ChatDeletion(Base):
    __tablename__ = 'chat_deletions'
    chat_id: Mapped[int] = mapped_column(ForeignKey('direct_chats.id', ondelete='CASCADE'), primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey('users.telegram_id', ondelete='CASCADE'), primary_key=True)
    deleted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class BlockedUser(Base):
    __tablename__ = 'blocked_users'
    blocker_id: Mapped[int] = mapped_column(BigInteger, ForeignKey('users.telegram_id', ondelete='CASCADE'), primary_key=True)
    blocked_id: Mapped[int] = mapped_column(BigInteger, ForeignKey('users.telegram_id', ondelete='CASCADE'), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class UserPresence(Base):
    __tablename__ = 'user_presence'
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey('users.telegram_id', ondelete='CASCADE'), primary_key=True)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
