import unittest

from app.services.stars_pricing import CURRENCY, stars_price


class StarsPricingTests(unittest.TestCase):
    def test_approved_prices(self):
        self.assertEqual(CURRENCY, 'XTR')
        for tier, prices in [('gold', [50, 150, 350]), ('plus', [75, 250, 600])]:
            for days, amount in zip([7, 30, 90], prices):
                self.assertEqual(stars_price(tier, days), amount)

    def test_unknown_plan_is_rejected(self):
        for tier, days in [('gold', 1), ('unknown', 7)]:
            with self.assertRaises(ValueError):
                stars_price(tier, days)
