import unittest
from types import SimpleNamespace as Obj
from unittest.mock import AsyncMock
from app.services.stars_orders import fulfill, valid


class StarsOrdersTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.order = Obj(user_id=42, amount=50, charge_id=None, tier='gold', days=7)
        self.user = Obj(gold_until=None, gold_plus_until=None)
        self.session = Obj(scalar=AsyncMock(side_effect=[self.order, self.user]), commit=AsyncMock())

    async def test_paid_subscription_and_duplicate(self):
        self.assertTrue(await fulfill(self.session, 'order', 42, 'XTR', 50, 'charge'))
        expiry = self.user.gold_until
        self.assertEqual(self.order.charge_id, 'charge')
        self.session.scalar.side_effect = [self.order]
        self.assertFalse(await fulfill(self.session, 'order', 42, 'XTR', 50, 'charge'))
        self.assertEqual(expiry, self.user.gold_until)
        self.session.commit.assert_awaited_once()

    async def test_wrong_user_currency_or_amount(self):
        for uid, currency, amount in [(43, 'XTR', 50), (42, 'USD', 50), (42, 'XTR', 1)]:
            self.assertFalse(valid(self.order, uid, currency, amount))
            self.session.scalar.side_effect = [self.order]
            with self.assertRaises(ValueError):
                await fulfill(self.session, 'order', uid, currency, amount, 'charge')
        self.session.commit.assert_not_awaited()

    async def test_different_charge_rejected(self):
        self.order.charge_id = 'first'
        self.session.scalar.side_effect = [self.order]
        with self.assertRaises(ValueError):
            await fulfill(self.session, 'order', 42, 'XTR', 50, 'second')

    async def test_plus_grant(self):
        self.order.tier = 'plus'
        await fulfill(self.session, 'order', 42, 'XTR', 50, 'charge')
        self.assertIsNotNone(self.user.gold_plus_until)
