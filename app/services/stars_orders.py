"""Durable, single-use Stars invoices and idempotent subscription delivery."""
from datetime import UTC, datetime
from uuid import uuid4
from sqlalchemy import String, Integer, BigInteger, DateTime, select
from sqlalchemy.orm import Mapped, mapped_column
from app.models import Base, User
from app.services.stars_pricing import stars_price
from app.services.subscriptions import grant_subscription


class StarsOrder(Base):
    __tablename__ = 'stars_orders'
    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    tier: Mapped[str] = mapped_column(String(8))
    days: Mapped[int] = mapped_column(Integer)
    amount: Mapped[int] = mapped_column(Integer)
    charge_id: Mapped[str | None] = mapped_column(String(255), unique=True)
    created: Mapped[datetime] = mapped_column(DateTime(timezone=True))


def valid(order, uid, currency, amount):
    return bool(order and order.user_id == uid and currency == 'XTR'
                and order.amount == amount)


async def create(session, uid, tier, days):
    order = StarsOrder(id=uuid4().hex, user_id=uid, tier=tier, days=days,
                       amount=stars_price(tier, days), created=datetime.now(UTC))
    session.add(order)
    await session.commit()
    return order


async def fulfill(session, payload, uid, currency, amount, charge):
    order = await session.scalar(select(StarsOrder).where(StarsOrder.id == payload).with_for_update())
    if not valid(order, uid, currency, amount):
        raise ValueError('Invalid Stars payment')
    if order.charge_id:
        if order.charge_id != charge:
            raise ValueError('Order already paid with another charge')
        return False
    user = await session.scalar(select(User).where(User.telegram_id == uid).with_for_update())
    if not user:
        raise ValueError('Payment user missing')
    grant_subscription(user, order.tier, order.days)
    order.charge_id = charge
    await session.commit()
    return True
