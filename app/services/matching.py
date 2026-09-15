from datetime import UTC, datetime, timedelta
from sqlalchemy import delete, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import settings
from app.models import ChatInvitation, Match, MatchQueue, MiniMessage, User
from app.services.users import age_on

async def leave_queue(session: AsyncSession, user_id: int):
    await session.execute(delete(ChatInvitation).where(or_(ChatInvitation.sender_id == user_id, ChatInvitation.recipient_id == user_id)))
    await session.execute(delete(MatchQueue).where(MatchQueue.user_id == user_id))

async def find_or_queue(session: AsyncSession, user: User, mode: str, city: str | None, min_age: int | None, max_age: int | None, archive_consent: bool = False):
    await leave_queue(session, user.telegram_id)
    mini = mode in ('mini_anonymous', 'mini_open')
    query = select(MatchQueue).where(MatchQueue.user_id != user.telegram_id)
    if mini:
        query = query.where(MatchQueue.mode.in_(['mini_anonymous', 'mini_open']), MatchQueue.queued_at >= datetime.now(UTC) - timedelta(seconds=30))
        city = min_age = max_age = None
    else:
        query = query.where(MatchQueue.mode == mode)
    candidates = (await session.scalars(query.order_by(MatchQueue.queued_at))).all()
    for candidate in candidates:
        if mini and archive_consent and not candidate.archive_consent:
            continue
        partner = await session.get(User, candidate.user_id)
        if not partner or not partner.is_registered or partner.is_banned: continue
        partner_age = age_on(partner.birth_date) if partner.birth_date else 0
        own_age = age_on(user.birth_date) if user.birth_date else 0
        # Both people's filters must be met.
        if not mini:
            if city and partner.city != city or candidate.city_filter and user.city != candidate.city_filter: continue
            if min_age and partner_age < min_age or max_age and partner_age > max_age: continue
            if candidate.min_age and own_age < candidate.min_age or candidate.max_age and own_age > candidate.max_age: continue
        await leave_queue(session, partner.telegram_id)
        match_mode = ('mini_' + ('a' if mode == 'mini_anonymous' else 'o') + ('a' if candidate.mode == 'mini_anonymous' else 'o')) if mini else mode
        match = Match(user_one_id=user.telegram_id, user_two_id=partner.telegram_id, mode=match_mode,
                      archive_consent=bool(mini and archive_consent and candidate.archive_consent))
        session.add(match); await session.flush()
        return match, partner
    session.add(MatchQueue(user_id=user.telegram_id, mode=mode, city_filter=city, min_age=min_age, max_age=max_age, archive_consent=archive_consent))
    return None, None

def is_anonymous(match: Match, user_id: int) -> bool:
    # Older matches stored one shared mode; new matches retain each person's choice.
    if match.mode in ('mini_aa', 'mini_ao', 'mini_oa', 'mini_oo'):
        return match.mode[5 if user_id == match.user_one_id else 6] == 'a'
    return match.mode != 'mini_open'

def set_anonymous(match: Match, user_id: int, anonymous: bool):
    one = anonymous if user_id == match.user_one_id else is_anonymous(match, match.user_one_id)
    two = anonymous if user_id == match.user_two_id else is_anonymous(match, match.user_two_id)
    match.mode = 'mini_' + ('a' if one else 'o') + ('a' if two else 'o')

async def active_match(session: AsyncSession, user_id: int):
    return await session.scalar(select(Match).where(Match.status == "active", or_(Match.user_one_id == user_id, Match.user_two_id == user_id)))

async def end_match(session: AsyncSession, match: Match):
    match.status, match.ended_at = "ended", datetime.now(UTC)
    if match.mode.startswith('mini_'):
        if settings().archive_channel_id and match.archive_consent:
            from app.services.archive import enqueue_chat
            await enqueue_chat(session, match)
        else:
            await session.execute(delete(MiniMessage).where(MiniMessage.match_id == match.id))
