import unittest
from datetime import UTC, datetime, timedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.models import Base, User, UserUsername, UsernamePurchase
from app.services.username_purchases import normalize, reconcile_usernames


class PurchaseTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine('sqlite+aiosqlite:///:memory:')
        async with self.engine.begin() as c:
            await c.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        self.now = datetime.now(UTC)

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def test_downgrade_paid_slot_and_restore(self):
        async with self.sessions() as s:
            u=User(telegram_id=42,app_username='a',is_verified=False,silver_verified=False,
                   gold_until=self.now-timedelta(seconds=1),short_username_min_length=0)
            s.add(u)
            s.add(UsernamePurchase(username='a',user_id=42,granted_at=self.now,expires_at=None))
            for i in range(5):
                s.add(UserUsername(user_id=42,username='handle'+str(i),position=i+1))
            await s.commit()
            await normalize(s,u,self.now)
            rows=list((await s.scalars(select(UserUsername))).all())
            self.assertEqual(u.app_username,'a')
            self.assertEqual(sum(r.hidden_until is None for r in rows),1)
            self.assertEqual(sum(r.hidden_until is not None for r in rows),4)
            u.gold_until=self.now+timedelta(days=7)
            u.gold_plus_until=self.now+timedelta(days=7)
            await normalize(s,u,self.now+timedelta(days=1))
            self.assertTrue(all(r.hidden_until is None for r in (await s.scalars(select(UserUsername))).all()))

    async def test_purchase_expiry_and_release(self):
        async with self.sessions() as s:
            u=User(telegram_id=42,app_username='a',is_verified=False,silver_verified=False,
                   short_username_access=True,short_username_min_length=1)
            s.add(u)
            s.add(UsernamePurchase(username='a',user_id=42,granted_at=self.now-timedelta(days=30),expires_at=self.now))
            await s.commit()
            await normalize(s,u,self.now)
            self.assertIsNone(u.app_username)
            self.assertEqual(len((await s.scalars(select(UserUsername))).all()),1)
            await normalize(s,u,self.now+timedelta(days=4))
            self.assertEqual((await s.scalars(select(UserUsername))).all(),[])

    async def test_background_expiry_without_profile_visit(self):
        async with self.sessions() as s:
            s.add(User(telegram_id=42, app_username='a', is_verified=False,
                       silver_verified=False, short_username_access=True, short_username_min_length=1))
            s.add(UsernamePurchase(username='a', user_id=42, granted_at=self.now-timedelta(days=31),
                                   expires_at=self.now-timedelta(seconds=1)))
            await s.commit()
        await reconcile_usernames(self.sessions, self.now, batch_size=1)
        async with self.sessions() as s:
            self.assertIsNone((await s.get(User,42)).app_username)
            rows = (await s.scalars(select(UserUsername))).all()
            self.assertEqual(len(rows),1)
            self.assertIsNotNone(rows[0].hidden_until)
        await reconcile_usernames(self.sessions, self.now+timedelta(days=4))
        async with self.sessions() as s:
            self.assertEqual((await s.scalars(select(UserUsername))).all(),[])
