"""Gold expiry includes the reserved Gold time after a Plus period."""
from datetime import UTC, datetime, timedelta


def aware(value):
    return value.replace(tzinfo=UTC) if value and value.tzinfo is None else value


def subscription(user, now=None):
    now = now or datetime.now(UTC)
    gold = aware(getattr(user, 'gold_until', None))
    plus = aware(getattr(user, 'gold_plus_until', None))
    is_plus = bool(plus and plus > now)
    return {
        'tier': 'plus' if is_plus else 'gold' if gold and gold > now else 'free',
        'gold_until': gold,
        'gold_plus_until': plus,
        'saved_gold_seconds': max(0, int((gold - plus).total_seconds())) if is_plus and gold else 0,
    }


def grant_subscription(user, kind, days, now=None):
    if kind not in ('gold', 'plus') or days <= 0:
        raise ValueError('Invalid subscription grant')
    now = now or datetime.now(UTC)
    duration = timedelta(days=days)
    # Extending both deadlines freezes the remaining Gold duration during Plus.
    user.gold_until = max(aware(user.gold_until) or now, aware(getattr(user, 'gold_plus_until', None)) or now, now) + duration
    if kind == 'plus':
        user.gold_plus_until = max(aware(getattr(user, 'gold_plus_until', None)) or now, now) + duration


def limits(user):
    tier = subscription(user)['tier']
    verified = bool(user.is_verified)
    return {
        'roulette': 100 if tier == 'plus' else 20 if tier == 'gold' else 10,
        'usernames': 999 if verified else 5 if tier == 'plus' else 2 if tier == 'gold' or user.silver_verified else 1,
        'username_min': 1 if verified else 5 if tier != 'free' else (user.short_username_min_length or (2 if user.silver_verified else 1)),
    }
