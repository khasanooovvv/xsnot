"""Serialized card queues. Attribution is by card, amount and time, not payer identity."""
import hashlib
import re
from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4
from sqlalchemy import String, Integer, BigInteger, DateTime, select, text
from sqlalchemy.orm import Mapped, mapped_column
from app.models import Base, User
from app.services.subscriptions import aware, grant_subscription

PRICES = {'gold': {7: 9900, 30: 29900, 90: 69900}, 'plus': {7: 14900, 30: 49900, 90: 119900}}
CARDS = {'UZCARD': '5614681885918346', 'HUMO': '9860356645379963'}


class CardOrder(Base):
    __tablename__ = 'card_orders'
    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    network: Mapped[str] = mapped_column(String(8))
    tier: Mapped[str] = mapped_column(String(8))
    days: Mapped[int] = mapped_column(Integer)
    amount: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(16), index=True)
    created: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    seen: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    started: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class CardReceipt(Base):
    __tablename__ = 'card_receipts'
    key: Mapped[str] = mapped_column(String(80), primary_key=True)
    fingerprint: Mapped[str] = mapped_column(String(64), unique=True)
    order_id: Mapped[str | None] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(16))
    body: Mapped[str] = mapped_column(String(4096))


async def lock(s):
    if s.bind.dialect.name == 'postgresql':
        await s.execute(text('SELECT pg_advisory_xact_lock(730029)'))
    else:
        await s.execute(text('BEGIN IMMEDIATE'))


async def refresh(s, now):
    orders = list((await s.scalars(select(CardOrder).where(CardOrder.status.in_(['active', 'queued'])).order_by(CardOrder.created, CardOrder.id))).all())
    for o in orders:
        if o.status == 'active' and aware(o.expires) <= now:
            o.status = 'expired'
        elif o.status == 'queued' and aware(o.seen) < now - timedelta(seconds=45):
            o.status = 'cancelled'
    await s.flush()
    return orders


async def order_state(s, uid, network=None, tier=None, days=None, order_id=None, switch=False):
    await lock(s)
    now = datetime.now(UTC)
    orders = await refresh(s, now)
    if order_id:
        o = await s.get(CardOrder, order_id)
        if not o or o.user_id != uid:
            raise ValueError('Buyurtma topilmadi')
    else:
        o = next((x for x in orders if x.user_id == uid and x.status in ('active', 'queued')), None)
        if o and switch and o.status == 'queued':
            o.status = 'cancelled'
            o = None
        if not o:
            if network not in CARDS or tier not in PRICES or days not in PRICES[tier]:
                raise ValueError('Noto‘g‘ri tarif')
            o = CardOrder(id=uuid4().hex, user_id=uid, network=network, tier=tier, days=days,
                          amount=PRICES[tier][days], status='queued', created=now, seen=now)
            s.add(o)
            orders.append(o)
    o.seen = now
    queue = [x for x in orders if x.network == o.network and x.status == 'queued']
    busy = any(x.network == o.network and x.status == 'active' for x in orders)
    if o.status == 'queued' and not busy and queue and queue[0].id == o.id:
        o.status = 'active'
        o.started = now
        o.expires = now + timedelta(minutes=5)
    other = 'HUMO' if o.network == 'UZCARD' else 'UZCARD'
    result = dict(id=o.id, status=o.status, network=o.network, tier=o.tier, days=o.days, amount=o.amount,
                  remaining=max(0, int((aware(o.expires)-now).total_seconds())) if o.expires else 0,
                  position=1 + sum(x.network == o.network and x.status in ('queued', 'active') and x.id != o.id and aware(x.created) <= aware(o.created) for x in orders) if o.status == 'queued' else 0,
                  alternative=other if not any(x.network == other and x.status in ('active', 'queued') for x in orders) else None,
                  card=CARDS[o.network] if o.status == 'active' else None)
    await s.commit()
    return result


def parse_receipt(body):
    # Only incoming credits; never parse the balance line as the paid amount.
    amount = re.search(r'(?:\+|➕)\s*(\d[\d .,\u00a0]*[.,]\d{2})\s*UZS', body, re.I)
    card = re.search(r'\*+(8346|9963)\b', body)
    stamp = re.search(r'(\d{2}\.\d{2}\.(?:\d{4}|\d{2}))\s+(\d{2}:\d{2})', body)
    if not stamp:
        rev = re.search(r'(\d{2}:\d{2})\s+(\d{2}\.\d{2}\.(?:\d{4}|\d{2}))', body)
        if rev:
            date, hour = rev[2], rev[1]
        else:
            return None
    else:
        date, hour = stamp[1], stamp[2]
    if not amount or not card:
        return None
    raw = amount[1].replace(' ', '').replace('\u00a0', '')
    raw = raw[:-3].replace(',', '').replace('.', '') + '.' + raw[-2:]
    value = Decimal(raw)
    if value != int(value):
        return None
    fmt = '%d.%m.%Y %H:%M' if len(date) == 10 else '%d.%m.%y %H:%M'
    try:
        at = datetime.strptime(date + ' ' + hour, fmt).replace(tzinfo=timezone(timedelta(hours=5))).astimezone(UTC)
    except ValueError:
        return None
    return ('UZCARD' if card[1] == '8346' else 'HUMO', int(value), at)


async def receive(s, channel, message_id, body, posted, now=None):
    await lock(s)
    now = now or datetime.now(UTC)
    key = f'{channel}:{message_id}'
    fingerprint = hashlib.sha256(' '.join(body.split()).encode()).hexdigest()
    if await s.get(CardReceipt, key) or await s.scalar(select(CardReceipt).where(CardReceipt.fingerprint == fingerprint)):
        return None
    receipt = CardReceipt(key=key, fingerprint=fingerprint, status='review', body=body[:4096])
    s.add(receipt)
    parsed = parse_receipt(body)
    matched = None
    if parsed:
        network, amount, bank_time = parsed
        o = await s.scalar(select(CardOrder).where(CardOrder.network == network, CardOrder.status == 'active'))
        if (o and o.amount == amount and aware(o.started) <= posted < aware(o.expires)
                and now < aware(o.expires) and aware(o.started).replace(second=0, microsecond=0) <= bank_time < aware(o.expires)
                and timedelta(0) <= posted - bank_time < timedelta(minutes=2)):
            user = await s.scalar(select(User).where(User.telegram_id == o.user_id).with_for_update())
            if user and not user.is_banned:
                grant_subscription(user, o.tier, o.days, now)
                o.status = 'paid'
                receipt.status = 'paid'
                receipt.order_id = o.id
                matched = o.user_id
    await s.commit()
    return matched
