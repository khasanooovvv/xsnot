import unittest
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import patch
from app.services.badges import badge_status, days_left

class BadgeStateTests(unittest.TestCase):
    def setUp(self):
        self.now=datetime(2026,9,13,12,tzinfo=UTC)
        self.clock=patch('app.services.badges.datetime')
        clock=self.clock.start();clock.now.return_value=self.now
        self.addCleanup(self.clock.stop)

    def test_expired_and_exact_expiry_have_no_badge(self):
        for until in (None,self.now,self.now-timedelta(seconds=1)):
            self.assertEqual(days_left(until),0)

    def test_partial_day_and_exact_day(self):
        self.assertEqual(days_left(self.now+timedelta(seconds=1)),1)
        self.assertEqual(days_left(self.now+timedelta(days=30)),30)
        self.assertEqual(days_left((self.now+timedelta(days=1)).replace(tzinfo=None)),1)

    def test_existing_premium_is_silver_and_does_not_verify(self):
        user=SimpleNamespace(premium_until=self.now+timedelta(days=20),gold_until=None,is_verified=False)
        self.assertEqual(badge_status(user),dict(silver=20,gold=0,verified=False))

    def test_admin_verification_survives_subscription_expiry(self):
        user=SimpleNamespace(premium_until=self.now,gold_until=self.now,is_verified=True)
        self.assertEqual(badge_status(user),dict(silver=0,gold=0,verified=True))
