from datetime import UTC, datetime
from sqlalchemy import delete, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Match, MatchQueue, User
from app.services.users import age_on

async def leave_queue(session: AsyncSession, user_id: int):
    await session.execute(delete(MatchQueue).where(MatchQueue.user_id == user_id))

async def find_or_queue(session: AsyncSession, user: User, mode: str, city: str | None, min_age: int | None, max_age: int | None):
    await leave_queue(session, user.telegram_id)
    candidates = (await session.scalars(select(MatchQueue).where(MatchQueue.mode == mode, MatchQueue.user_id != user.telegram_id).order_by(MatchQueue.queued_at))).all()
    for candidate in candidates:
        partner = await session.get(User, candidate.user_id)
        if not partner or not partner.is_registered or partner.is_banned: continue
        partner_age = age_on(partner.birth_date) if partner.birth_date else 0
        own_age = age_on(user.birth_date) if user.birth_date else 0
        # Both people's filters must be met.
        if city and partner.city != city or candidate.city_filter and user.city != candidate.city_filter: continue
        if min_age and partner_age < min_age or max_age and partner_age > max_age: continue
        if candidate.min_age and own_age < candidate.min_age or candidate.max_age and own_age > candidate.max_age: continue
        await leave_queue(session, partner.telegram_id)
        match = Match(user_one_id=user.telegram_id, user_two_id=partner.telegram_id, mode=mode)
        session.add(match); await session.flush()
        return match, partner
    session.add(MatchQueue(user_id=user.telegram_id, mode=mode, city_filter=city, min_age=min_age, max_age=max_age))
    return None, None

async def active_match(session: AsyncSession, user_id: int):
    return await session.scalar(select(Match).where(Match.status == "active", or_(Match.user_one_id == user_id, Match.user_two_id == user_id)))

async def end_match(session: AsyncSession, match: Match):
    match.status, match.ended_at = "ended", datetime.now(UTC)
