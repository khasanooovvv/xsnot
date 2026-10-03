"""Approved subscription prices in Telegram Stars (not a live exchange rate)."""

CURRENCY = 'XTR'
STARS_PRICES = {
    'gold': {7: 50, 30: 150, 90: 350},
    'plus': {7: 75, 30: 250, 90: 600},
}


def stars_price(tier: str, days: int) -> int:
    """Return the integer invoice amount; reject unsupported plans."""
    try:
        return STARS_PRICES[tier][days]
    except KeyError as error:
        raise ValueError('Unsupported Stars subscription plan') from error
