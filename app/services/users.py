from datetime import UTC, date, datetime, timedelta
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import settings
from app.models import ReferralHistory, ReferralShare, User
from app.services.badges import days_left

def age_on(born: date) -> int:
    today = date.today()
    return today.year - born.year - ((today.month, today.day) < (born.month, born.day))

async def get_or_create(session: AsyncSession, user_id: int, username: str | None, name: str, referrer: int | None):
    if session.bind.dialect.name == "postgresql":
        await session.execute(text("SELECT pg_advisory_xact_lock(:user_id)"), {"user_id": user_id})
    user = await session.get(User, user_id)
    if user:
        user._new_referral = False
        user.username = username
        if not user.is_registered:
            user.display_name = name
        return user
    valid = referrer if referrer and 0 < referrer < 2**63 and referrer != user_id and await session.get(User, referrer) else None
    prior_referral = await session.scalar(select(ReferralHistory.id).where(ReferralHistory.referred_id == user_id))
    repeat_referral = bool(valid and prior_referral)
    user = User(telegram_id=user_id, username=username, display_name=name, referred_by_id=valid)
    user._new_referral = bool(valid)
    user._repeat_referral = repeat_referral
    session.add(user); await session.flush()
    return user

async def referral_count(session: AsyncSession, user_id: int) -> int:
    return int(await session.scalar(select(func.count(ReferralHistory.id)).where(ReferralHistory.referrer_id == user_id, ReferralHistory.active.is_(True))) or 0)

async def apply_referral_reward(session: AsyncSession, user: User):
    if user.referral_rewarded or not user.referred_by_id: return
    referrer = await session.get(User, user.referred_by_id)
    if not referrer: return
    user.referral_rewarded = True
    # A Telegram account can complete only one referral ever, even after deleting
    # and recreating its profile or opening another user's invite link.
    existing_history = await session.scalar(select(ReferralHistory).where(ReferralHistory.referred_id == user.telegram_id))
    if existing_history:
        return
    session.add(ReferralHistory(referrer_id=referrer.telegram_id, referred_id=user.telegram_id, referred_name=user.display_name))
    count = await referral_count(session, referrer.telegram_id)
    now = datetime.now(UTC)
    reward_days = {3: 3, 15: 15, 30: 30}.get(count)
    if reward_days:
        referrer.gold_until = max(referrer.gold_until or now, now) + timedelta(days=reward_days)

async def consume_share(session: AsyncSession, user_id: int) -> bool:
    today = date.today()
    item = await session.scalar(select(ReferralShare).where(ReferralShare.user_id == user_id, ReferralShare.share_day == today))
    if not item:
        item = ReferralShare(user_id=user_id, share_day=today); session.add(item); await session.flush()
    user = await session.get(User, user_id)
    if user.is_verified:
        item.count += 1
        return True
    limit = settings().silver_referral_daily_share_limit if user.silver_verified else settings().referral_daily_share_limit
    if item.count >= limit: return False
    item.count += 1
    return True
