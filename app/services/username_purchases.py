"""Explicit username-bound purchases; NULL expiry means permanent."""
from datetime import UTC, datetime, timedelta
from sqlalchemy import select, or_
from app.models import UsernamePurchase, UserUsername, User
from app.services.subscriptions import aware, limits


async def active_purchases(session, uid, now=None):
    now = now or datetime.now(UTC)
    rows = (await session.scalars(select(UsernamePurchase).where(
        UsernamePurchase.user_id == uid,
        or_(UsernamePurchase.expires_at.is_(None), UsernamePurchase.expires_at > now)))).all()
    return {row.username: row for row in rows}


async def normalize(session, user, now=None):
    """Keep paid slots independent, reserve downgraded handles for three days."""
    now = now or datetime.now(UTC)
    bought = await active_purchases(session, user.telegram_id, now)
    rows = list((await session.scalars(select(UserUsername).where(
        UserUsername.user_id == user.telegram_id).order_by(UserUsername.position, UserUsername.id))).all())
    # Move primary into the same ordered representation before applying limits.
    primary = user.app_username
    if primary and not any(row.username == primary for row in rows):
        rows.insert(0, UserUsername(user_id=user.telegram_id, username=primary, position=0))
    if user.gold_hidden_username and not any(row.username == user.gold_hidden_username for row in rows):
        rows.insert(0, UserUsername(user_id=user.telegram_id, username=user.gold_hidden_username,
                                   position=0, hidden_until=user.gold_hidden_username_until))
    policy = limits(user)
    count = 0
    kept = []
    expired_purchases = {row.username: aware(row.expires_at) for row in (await session.scalars(select(UsernamePurchase).where(
        UsernamePurchase.user_id == user.telegram_id, UsernamePurchase.expires_at <= now))).all()}
    for row in rows:
        deadline = aware(row.hidden_until)
        if row.username in expired_purchases:
            deadline = expired_purchases[row.username] + timedelta(days=3)
            row.hidden_until = deadline
        if deadline and deadline <= now and row.username not in bought:
            if row in session:
                await session.delete(row)
            continue
        paid = row.username in bought
        # Expired purchased short handles cannot use an old blanket permission.
        allowed = paid or (row.username not in expired_purchases and
                           len(row.username) >= policy['username_min'] and count < policy['usernames'])
        if allowed:
            row.hidden_until = None
            if not paid:
                count += 1
        elif not deadline:
            row.hidden_until = now + timedelta(days=3)
        kept.append(row)
    user.app_username = None
    user.gold_hidden_username = None
    user.gold_hidden_username_until = None
    # Flush unique primary before moving it to extras or promoting an extra.
    await session.flush()
    active = [row for row in kept if row.hidden_until is None]
    new_primary = next((row for row in active if row.username == primary), active[0] if active else None)
    for position, row in enumerate(kept):
        if row is new_primary:
            if row in session:
                await session.delete(row)
        else:
            row.position = position + 1
            session.add(row)
    await session.flush()
    user.app_username = new_primary.username if new_primary else None
    await session.flush()


async def reconcile_usernames(sessions=None, now=None, batch_size=100):
    """Reconcile assignments without requiring owners to open their profiles."""
    from app.database import SessionLocal
    sessions = sessions or SessionLocal
    now = now or datetime.now(UTC)
    cursor = None
    while True:
        async with sessions() as session:
            query = select(User.telegram_id).where(or_(
                User.app_username.is_not(None), User.gold_hidden_username.is_not(None),
                User.telegram_id.in_(select(UserUsername.user_id))))
            if cursor is not None:
                query = query.where(User.telegram_id > cursor)
            ids = list((await session.scalars(query.order_by(User.telegram_id).limit(batch_size))).all())
        if not ids:
            return
        for uid in ids:
            async with sessions() as session:
                user = await session.get(User, uid, with_for_update=True)
                if user:
                    await normalize(session, user, now)
                    await session.commit()
        cursor = ids[-1]


async def username_worker():
    import asyncio
    import logging
    while True:
        try:
            await reconcile_usernames()
        except Exception:
            logging.getLogger(__name__).exception('Username reconciliation failed')
        await asyncio.sleep(60)
