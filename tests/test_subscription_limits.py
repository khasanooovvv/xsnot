import os
os.environ['BOT_TOKEN'] = '123:test'
os.environ['DATABASE_URL'] = 'sqlite+aiosqlite:///:memory:'
import unittest
from datetime import UTC, datetime, timedelta
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.models import Base, User
from app.direct_models import DirectQuota
from app.services.subscriptions import subscription, grant_subscription, limits
from app.services.direct_quota import direct_permission


class SubscriptionTests(unittest.TestCase):
    def test_plus_pauses_gold_and_repeated_purchases(self):
        now = datetime.now(UTC)
        u = User(gold_until=now+timedelta(days=90))
        grant_subscription(u, 'plus', 7, now)
        self.assertEqual(subscription(u, now)['saved_gold_seconds'], 90*86400)
        self.assertEqual(u.gold_plus_until, now+timedelta(days=7))
        self.assertEqual(subscription(u, now+timedelta(days=7))['tier'], 'gold')
        self.assertEqual(u.gold_until-(now+timedelta(days=7)), timedelta(days=90))
        grant_subscription(u, 'plus', 7, now+timedelta(days=1))
        self.assertEqual(u.gold_plus_until, now+timedelta(days=14))
        self.assertEqual(subscription(u, now)['saved_gold_seconds'], 90*86400)
        grant_subscription(u, 'gold', 3, now)
        self.assertEqual(subscription(u, now)['saved_gold_seconds'], 93*86400)

    def test_all_tiers(self):
        u = User(is_verified=False, silver_verified=False, short_username_min_length=0)
        self.assertEqual(limits(u)['roulette'], 10)
        grant_subscription(u, 'gold', 7)
        self.assertEqual(limits(u), {'roulette':20, 'usernames':2, 'username_min':5})
        grant_subscription(u, 'plus', 7)
        self.assertEqual(limits(u), {'roulette':100, 'usernames':5, 'username_min':5})


class QuotaTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine('sqlite+aiosqlite:///:memory:')
        async with self.engine.begin() as c:
            await c.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        self.now = datetime.now(UTC)
        async with self.sessions() as s:
            s.add(User(telegram_id=1, gold_until=self.now+timedelta(days=90)))
            await s.commit()

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def permission(self, other, consume=True, offset=0):
        async with self.sessions() as s:
            u = await s.get(User, 1)
            result = await direct_permission(s, u, other, consume, self.now+timedelta(days=offset))
            await s.commit()
            return result

    async def test_three_partners_reading_repeat_and_week_reset(self):
        self.assertTrue((await self.permission(99, False))['allowed'])
        async with self.sessions() as s:
            self.assertIsNone(await s.get(DirectQuota, 1))
        for other in [2, 3, 4, 2, 3]:
            self.assertTrue((await self.permission(other))['allowed'])
        denied = await self.permission(5)
        self.assertFalse(denied['allowed'])
        self.assertEqual(denied['resets_at'], self.now+timedelta(days=7))
        self.assertTrue((await self.permission(5, offset=7))['allowed'])

    async def test_plus_unlimited_and_downgrade_preserves_gold_window(self):
        for other in [2, 3, 4]:
            await self.permission(other)
        async with self.sessions() as s:
            u = await s.get(User, 1)
            grant_subscription(u, 'plus', 1, self.now)
            await s.commit()
        for other in range(5, 30):
            self.assertTrue((await self.permission(other))['allowed'])
        self.assertFalse((await self.permission(5, offset=1))['allowed'])
        self.assertTrue((await self.permission(2, offset=1))['allowed'])
