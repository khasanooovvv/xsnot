"""Dating profiles are independent of roulette and subscription tiers."""
from sqlalchemy import BigInteger, Boolean, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.models import Base


class DatingProfile(Base):
    __tablename__ = 'dating_profiles'
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey('users.telegram_id', ondelete='CASCADE'), primary_key=True)
    bio: Mapped[str] = mapped_column(String(300), default='')
    photos: Mapped[str] = mapped_column(Text, default='[]')


class DatingVote(Base):
    __tablename__ = 'dating_votes'
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey('users.telegram_id', ondelete='CASCADE'), primary_key=True)
    target_id: Mapped[int] = mapped_column(BigInteger, ForeignKey('users.telegram_id', ondelete='CASCADE'), primary_key=True)
    liked: Mapped[bool] = mapped_column(Boolean)
