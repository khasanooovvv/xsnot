from __future__ import annotations
from datetime import date, datetime
from sqlalchemy import LargeBinary, BigInteger, Boolean, Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

class Base(DeclarativeBase): pass

class User(Base):
    __tablename__ = "users"
    telegram_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    username: Mapped[str | None] = mapped_column(String(64))
    display_name: Mapped[str] = mapped_column(String(128), default="Player")
    language: Mapped[str] = mapped_column(String(2), default="uz")
    birth_date: Mapped[date | None] = mapped_column(Date)
    city: Mapped[str | None] = mapped_column(String(100))
    avatar_file_id: Mapped[str | None] = mapped_column(String(255))
    avatar_is_default: Mapped[bool] = mapped_column(Boolean, default=True)
    terms_accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    terms_version: Mapped[str | None] = mapped_column(String(32))
    archive_consent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_registered: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    is_banned: Mapped[bool] = mapped_column(Boolean, default=False)
    muted_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    silver_verified: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    premium_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    gold_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    referred_by_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.telegram_id"))
    referral_rewarded: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    referrer: Mapped["User | None"] = relationship(remote_side=[telegram_id])

class MatchQueue(Base):
    __tablename__ = "match_queue"
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.telegram_id"), primary_key=True)
    mode: Mapped[str] = mapped_column(String(16))
    archive_consent: Mapped[bool] = mapped_column(Boolean, default=False, server_default='false')
    city_filter: Mapped[str | None] = mapped_column(String(100))
    min_age: Mapped[int | None] = mapped_column(Integer)
    max_age: Mapped[int | None] = mapped_column(Integer)
    queued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class Match(Base):
    __tablename__ = "matches"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_one_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.telegram_id"), index=True)
    user_two_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.telegram_id"), index=True)
    mode: Mapped[str] = mapped_column(String(16))
    archive_consent: Mapped[bool] = mapped_column(Boolean, default=False, server_default='false')
    status: Mapped[str] = mapped_column(String(16), default="active")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

class Report(Base):
    __tablename__ = "reports"
    id: Mapped[int] = mapped_column(primary_key=True)
    reporter_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.telegram_id"))
    reported_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.telegram_id"))
    match_id: Mapped[int | None] = mapped_column(ForeignKey("matches.id"))
    reason: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class ReferralShare(Base):
    __tablename__ = "referral_shares"
    __table_args__ = (UniqueConstraint("user_id", "share_day", name="daily_referral_share"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.telegram_id"))
    share_day: Mapped[date] = mapped_column(Date)
    count: Mapped[int] = mapped_column(Integer, default=0)

class ReferralHistory(Base):
    __tablename__ = "referral_history"
    __table_args__ = (UniqueConstraint("referrer_id", "referred_id", name="unique_referral_history"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    referrer_id: Mapped[int] = mapped_column(BigInteger, index=True)
    referred_id: Mapped[int] = mapped_column(BigInteger, index=True)
    referred_name: Mapped[str | None] = mapped_column(String(128))
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class MiniAvatar(Base):
    __tablename__ = "mini_avatars"
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.telegram_id"), primary_key=True)
    data: Mapped[str] = mapped_column(Text)

class MiniMessage(Base):
    __tablename__ = "mini_messages"
    id: Mapped[int] = mapped_column(primary_key=True)
    match_id: Mapped[int] = mapped_column(ForeignKey("matches.id"), index=True)
    sender_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.telegram_id"))
    text: Mapped[str] = mapped_column(Text)

class VideoVerification(Base):
    __tablename__ = "video_verifications"
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.telegram_id"), primary_key=True)
    status: Mapped[str] = mapped_column(String(16), default="draft")
    challenge: Mapped[str] = mapped_column(String(6))
    challenge_until: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    video: Mapped[bytes | None] = mapped_column(LargeBinary)
    media_type: Mapped[str | None] = mapped_column(String(32))
    consent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reason: Mapped[str | None] = mapped_column(String(500))

class ArchiveDelivery(Base):
    __tablename__ = 'archive_deliveries'
    id: Mapped[int] = mapped_column(primary_key=True)
    event_key: Mapped[str] = mapped_column(String(160), unique=True)
    channel_id: Mapped[str] = mapped_column(String(128))
    media_type: Mapped[str] = mapped_column(String(32))
    filename: Mapped[str] = mapped_column(String(160))
    caption: Mapped[str] = mapped_column(Text)
    payload: Mapped[bytes | None] = mapped_column(LargeBinary)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    next_attempt_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    message_id: Mapped[int | None] = mapped_column(BigInteger)
