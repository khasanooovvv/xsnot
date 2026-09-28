import unittest
from datetime import UTC, datetime, timedelta, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.models import Base, User
from app.services.card_orders import CardOrder, CardReceipt, order_state, receive, parse_receipt


class CardOrderTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine('sqlite+aiosqlite:///:memory:')
        async with self.engine.begin() as c:
            await c.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        async with self.sessions() as s:
            s.add_all([User(telegram_id=i, display_name=str(i)) for i in (1, 2, 3)])
            await s.commit()

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def create(self, uid=1, network='UZCARD', tier='gold', days=7, **kw):
        async with self.sessions() as s:
            return await order_state(s, uid, network, tier, days, **kw)

    async def state(self, uid, oid):
        async with self.sessions() as s:
            return await order_state(s, uid, order_id=oid)

    def body(self, amount='9 900.00', card='8346', at=None):
        stamp = (at or datetime.now(UTC)).astimezone(timezone(timedelta(hours=5))).strftime('%d.%m.%y %H:%M')
        return f'🟢 Perevod na kartu\n➕ {amount} UZS\n💳 ***{card}\n🕒 {stamp}\n💰 32 203.52 UZS'

    async def credit(self, body=None, mid=1):
        async with self.sessions() as s:
            return await receive(s, -1003949300805, mid, body or self.body(), datetime.now(UTC))

    async def test_queue_per_card_and_reopen(self):
        a = await self.create()
        b = await self.create(2)
        c = await self.create(3, 'HUMO')
        self.assertEqual((a['status'], b['status'], c['status']), ('active', 'queued', 'active'))
        self.assertIsNone(b['card'])
        self.assertEqual(b['alternative'], 'HUMO')
        self.assertEqual((await self.create())['id'], a['id'])

    async def test_payment_granted_once_and_queue_advances(self):
        a = await self.create()
        b = await self.create(2)
        body = self.body()
        self.assertEqual(await self.credit(body), 1)
        async with self.sessions() as s:
            until = (await s.get(User, 1)).gold_until
        self.assertIsNone(await self.credit(body))
        self.assertIsNone(await self.credit(body, 2))
        async with self.sessions() as s:
            self.assertEqual((await s.get(User, 1)).gold_until, until)
        self.assertEqual((await self.state(1, a['id']))['status'], 'paid')
        self.assertEqual((await self.state(2, b['id']))['status'], 'active')

    async def test_wrong_amount_and_card_not_granted(self):
        await self.create()
        self.assertIsNone(await self.credit(self.body('14 900.00')))
        self.assertIsNone(await self.credit(self.body(card='9963'), 2))
        async with self.sessions() as s:
            self.assertIsNone((await s.get(User, 1)).gold_until)
            self.assertEqual(len((await s.scalars(select(CardReceipt))).all()), 2)

    async def test_expiry_releases_queue(self):
        a = await self.create()
        b = await self.create(2)
        async with self.sessions() as s:
            o = await s.get(CardOrder, a['id'])
            o.expires = datetime.now(UTC) - timedelta(seconds=1)
            await s.commit()
        self.assertIsNone(await self.credit())
        self.assertEqual((await self.state(1, a['id']))['status'], 'expired')
        self.assertEqual((await self.state(2, b['id']))['status'], 'active')

    async def test_owner_and_switch(self):
        a = await self.create()
        await self.create(2)
        with self.assertRaises(ValueError):
            await self.state(2, a['id'])
        b = await self.create(2, 'HUMO', switch=True)
        self.assertEqual((b['network'], b['status']), ('HUMO', 'active'))
        switched = await self.create(1, 'HUMO', switch=True)
        self.assertEqual((switched['network'], switched['status']), ('HUMO', 'queued'))
        self.assertEqual((await self.state(1, a['id']))['status'], 'cancelled')
        self.assertEqual((await self.create(1, 'HUMO', switch=True))['id'], switched['id'])

    async def test_active_switch_updates_card_and_preserves_same_card_timer(self):
        old = await self.create()
        new = await self.create(1, 'HUMO', switch=True)
        self.assertEqual((new['network'], new['card']), ('HUMO', '9860356645379963'))
        self.assertEqual((await self.state(1, old['id']))['status'], 'cancelled')
        reopened = await self.create(1, 'HUMO', switch=True)
        self.assertEqual(reopened['id'], new['id'])
        self.assertLessEqual(reopened['remaining'], new['remaining'])
        self.assertIsNone(await self.credit())
        self.assertEqual(await self.credit(self.body(card='9963'), 2), 1)

    async def test_old_receipt_not_granted(self):
        await self.create()
        self.assertIsNone(await self.credit(self.body(at=datetime.now(UTC)-timedelta(days=1))))

    async def test_plus_price_and_grant(self):
        await self.create(tier='plus', days=30)
        self.assertEqual(await self.credit(self.body('49 900.00')), 1)
        async with self.sessions() as s:
            self.assertIsNotNone((await s.get(User, 1)).gold_plus_until)

    async def test_api_validates_tariff_and_ownership(self):
        from unittest.mock import patch
        import httpx
        from fastapi import FastAPI
        from app import miniapp
        app = FastAPI()
        app.include_router(miniapp.router)
        app.dependency_overrides[miniapp.registered] = lambda: 1
        with patch.object(miniapp, 'SessionLocal', self.sessions):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test') as client:
                response = await client.post('/api/card-orders', json={'network':'UZCARD','tier':'gold','days':7,'amount':1})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()['amount'], 9900)
                oid = response.json()['id']
                bad = await client.post('/api/card-orders', json={'network':'UZCARD','tier':'gold','days':1})
                self.assertEqual(bad.status_code, 422)
                app.dependency_overrides[miniapp.registered] = lambda: 2
                denied = await client.get('/api/card-orders/' + oid)
                self.assertEqual(denied.status_code, 404)

    async def test_abandoned_queue_does_not_block(self):
        a = await self.create()
        b = await self.create(2)
        c = await self.create(3)
        async with self.sessions() as s:
            (await s.get(CardOrder, a['id'])).expires = datetime.now(UTC)-timedelta(seconds=1)
            (await s.get(CardOrder, b['id'])).seen = datetime.now(UTC)-timedelta(minutes=1)
            await s.commit()
        self.assertEqual((await self.state(3, c['id']))['status'], 'active')

    async def test_concurrent_creates_have_single_active_slot(self):
        import asyncio
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory(prefix='card-orders-') as folder:
            engine = create_async_engine('sqlite+aiosqlite:///' + (Path(folder) / 'orders.db').as_posix())
            try:
                async with engine.begin() as c:
                    await c.run_sync(Base.metadata.create_all)
                sessions = async_sessionmaker(engine, expire_on_commit=False)
                async def create(uid):
                    async with sessions() as s:
                        return await order_state(s, uid, 'UZCARD', 'gold', 7)
                results = await asyncio.gather(create(1), create(2), create(3))
                self.assertEqual(sum(r['status'] == 'active' for r in results), 1)
                self.assertEqual(sum(r['status'] == 'queued' for r in results), 2)
            finally:
                await engine.dispose()

    def test_humo_parser_and_balance_ignored(self):
        parsed = parse_receipt("🎉 To‘ldirish\n➕ 9,900,00 UZS\nHUMOCARD *9963\n22:51 23.09.2026\n💰 9.911,69 UZS")
        self.assertEqual(parsed[:2], ('HUMO', 9900))
        for amount in ('9.900,00', '9,900.00', '9\u00a0900.00'):
            self.assertEqual(parse_receipt(self.body(amount))[1], 9900)
        self.assertIsNone(parse_receipt('💰 9 900.00 UZS\n***8346\n23.09.26 22:50'))


if __name__ == '__main__':
    unittest.main()
