import json
from datetime import UTC, datetime, timedelta
from fastapi import HTTPException
from app.models import User
from app.direct_models import DirectQuota
from app.services.subscriptions import subscription, aware


async def direct_permission(session, user, other, consume=False, now=None):
    now = now or datetime.now(UTC)
    if consume:
        # The caller already loads the user in the same transaction. Reusing
        # that instance avoids SQLite's write-lock wait in the test database;
        # PostgreSQL transactions still serialize quota updates at commit.
        user = await session.get(User, user.telegram_id, populate_existing=True)
    tier = subscription(user, now)['tier']
    if tier == 'plus' or user.is_verified:
        return {'allowed': True, 'reason': None, 'resets_at': None}
    if tier == 'free':
        return {'allowed': False, 'reason': 'gold_required', 'resets_at': None}
    row = await session.get(DirectQuota, user.telegram_id)
    active = row and aware(row.started_at) + timedelta(days=7) > now
    recipients = json.loads(row.recipients) if active else []
    allowed = other in recipients or len(recipients) < 3
    if allowed and consume and other not in recipients:
        if not active:
            if row is None:
                row = DirectQuota(user_id=user.telegram_id)
                session.add(row)
            row.started_at = now
        recipients.append(other)
        row.recipients = json.dumps(recipients)
    return {'allowed': allowed, 'reason': None if allowed else 'weekly_dm_limit',
            'resets_at': aware(row.started_at) + timedelta(days=7) if row and (active or consume) else None}


async def require_direct_permission(session, user, other):
    permission = await direct_permission(session, user, other, consume=True)
    if not permission['allowed']:
        raise HTTPException(403, permission['reason'])
