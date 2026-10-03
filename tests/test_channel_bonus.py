import logging
import unittest
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace as Obj
from unittest.mock import AsyncMock
from test_chat_privacy import load_function
from app.services.subscriptions import subscription


class BonusTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.user = Obj(gold_until=None, gold_plus_until=None, channel_bonus_until=None)
        self.claim = None
        owner = self
        class Session:
            async def __aenter__(self): return self
            async def __aexit__(self, *args): pass
            async def get(self, model, uid, **kwargs):
                return owner.user if model is User else owner.claim
            def add(self, claim): owner.claim = claim
            commit = AsyncMock()
        class Claim:
            def __init__(self, **kwargs):
                self.revoked_at = None
                self.notified_at = None
                self.__dict__.update(kwargs)
        User = type('User', (), {})
        self.session = Session()
        ns = dict(SessionLocal=lambda: self.session, User=User, ChannelBonusClaim=Claim,
                  datetime=datetime, UTC=UTC, timedelta=timedelta, logging=logging)
        self.grant = load_function('app/services/channel_bonus.py', 'claim_bonus', ns)
        self.revoke = load_function('app/services/channel_bonus.py', 'revoke_bonus', ns)
        self.bot = Obj(send_message=AsyncMock())

    async def test_reward_once_and_revoke_preserves_paid_gold(self):
        paid = datetime.now(UTC) + timedelta(hours=3)
        self.user.gold_until = paid
        self.assertTrue(await self.grant(self.session, 1))
        deadline = self.user.channel_bonus_until
        self.assertEqual(subscription(self.user)['gold_until'], deadline)
        self.assertFalse(await self.grant(self.session, 1))
        self.assertEqual(self.user.channel_bonus_until, deadline)
        await self.revoke(self.bot, 1)
        self.assertIsNone(self.user.channel_bonus_until)
        self.assertEqual(self.user.gold_until, paid)
        self.assertEqual(subscription(self.user)['gold_until'], paid)
        self.assertFalse(await self.grant(self.session, 1))
        await self.revoke(self.bot, 1)
        self.bot.send_message.assert_awaited_once()

    async def test_bonus_alone_grants_then_removes_gold(self):
        await self.grant(self.session, 1)
        self.assertEqual(subscription(self.user)['tier'], 'gold')
        await self.revoke(self.bot, 1)
        self.assertEqual(subscription(self.user)['tier'], 'free')

    async def test_notification_failure_does_not_restore_reward(self):
        await self.grant(self.session, 1)
        self.bot.send_message.side_effect = OSError()
        await self.revoke(self.bot, 1)
        self.assertIsNotNone(self.claim.revoked_at)
        self.assertIsNone(self.claim.notified_at)
        self.assertIsNone(self.user.channel_bonus_until)
        self.bot.send_message.side_effect = None
        await self.revoke(self.bot, 1)
        self.assertIsNotNone(self.claim.notified_at)

    def test_only_members_qualify(self):
        check = load_function('app/services/channel_bonus.py', 'is_member', {})
        for status in ('creator', 'administrator', 'member'):
            self.assertTrue(check(Obj(status=status)))
        for status in ('left', 'kicked'):
            self.assertFalse(check(Obj(status=status)))
        self.assertTrue(check(Obj(status='restricted', is_member=True)))
        self.assertFalse(check(Obj(status='restricted', is_member=False)))
