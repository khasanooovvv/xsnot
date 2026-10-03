"""One-time membership reward, separate from purchased Gold."""
import logging
import asyncio
from datetime import UTC, datetime, timedelta
from app.database import SessionLocal
from app.models import ChannelBonusClaim, User
from sqlalchemy import select, or_

CHANNEL_ID = -1003995756842
CHANNEL_URL = 'https://t.me/xsbotnews'

def is_member(member):
    return member.status in ('creator', 'administrator', 'member') or (
        member.status == 'restricted' and bool(getattr(member, 'is_member', False)))

async def revoke_bonus(bot, uid):
    async with SessionLocal() as session:
        user = await session.get(User, uid, with_for_update=True)
        claim = await session.get(ChannelBonusClaim, uid, with_for_update=True)
        if not claim:
            return
        if not claim.revoked_at:
            claim.revoked_at = datetime.now(UTC)
            if user:
                user.channel_bonus_until = None
            await session.commit()
        if claim.notified_at:
            return
        try:
            await bot.send_message(uid, 'Kanalimizdan chiqqaningiz sababli 1 kunlik Gold bonusingiz bekor qilindi. Bu bonusni qayta olish mumkin emas. Sotib olingan Gold obunangiz o‘zgarmaydi.')
        except Exception:
            logging.getLogger(__name__).warning('Channel bonus notification failed for %s', uid)
            return
        claim.notified_at = datetime.now(UTC)
        await session.commit()

async def claim_bonus(session, uid):
    # User row serializes duplicate claims, including concurrent button clicks.
    user = await session.get(User, uid, with_for_update=True)
    claim = await session.get(ChannelBonusClaim, uid)
    if claim:
        return False
    now = datetime.now(UTC)
    session.add(ChannelBonusClaim(user_id=uid, claimed_at=now))
    user.channel_bonus_until = now + timedelta(days=1)
    await session.commit()
    return True

async def bonus_worker(bot):
    """Reconcile active rewards after missed events and retry failed notices."""
    while True:
        try:
            async with SessionLocal() as session:
                ids = list((await session.scalars(select(ChannelBonusClaim.user_id).outerjoin(
                    User, User.telegram_id == ChannelBonusClaim.user_id).where(or_(
                    User.channel_bonus_until > datetime.now(UTC),
                    ChannelBonusClaim.revoked_at.is_not(None) & ChannelBonusClaim.notified_at.is_(None))))).all())
            for uid in ids:
                try:
                    member = await bot.get_chat_member(CHANNEL_ID, uid)
                    if not is_member(member):
                        await revoke_bonus(bot, uid)
                    else:
                        async with SessionLocal() as session:
                            claim = await session.get(ChannelBonusClaim, uid)
                            retry = bool(claim and claim.revoked_at and not claim.notified_at)
                        if retry:
                            await revoke_bonus(bot, uid)
                except Exception:
                    logging.getLogger(__name__).warning('Membership check failed for %s', uid)
                await asyncio.sleep(.1)
        except Exception:
            logging.getLogger(__name__).exception('Channel bonus reconciliation failed')
        await asyncio.sleep(60)
