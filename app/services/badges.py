"""Public badge state; Silver reuses existing Premium subscription dates."""
from datetime import UTC, datetime
from math import ceil


def days_left(until: datetime | None) -> int:
    if until is None:
        return 0
    if until.tzinfo is None:
        until = until.replace(tzinfo=UTC)
    return max(0, ceil((until - datetime.now(UTC)).total_seconds() / 86400))


def badge_status(user) -> dict:
    return {
        'silver': days_left(user.premium_until),
        'gold': days_left(user.gold_until),
        'verified': bool(user.is_verified),
    }
