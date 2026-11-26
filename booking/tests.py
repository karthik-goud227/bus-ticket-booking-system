from decimal import Decimal

from django.test import SimpleTestCase

from .services import fare_breakdown


class FarePolicyTests(SimpleTestCase):
    def test_one_and_two_seats_change_service_fee_and_tax(self):
        one = fare_breakdown(Decimal("499.00"), 1)
        two = fare_breakdown(Decimal("499.00"), 2)
        self.assertEqual(one, {
            "base": Decimal("499.00"), "platform": Decimal("20.00"),
            "service": Decimal("9.98"), "gst": Decimal("5.40"),
            "total": Decimal("534.38"),
        })
        self.assertEqual(two, {
            "base": Decimal("998.00"), "platform": Decimal("20.00"),
            "service": Decimal("19.96"), "gst": Decimal("7.19"),
            "total": Decimal("1045.15"),
        })

    def test_rounds_each_percentage_to_paise(self):
        charges = fare_breakdown(Decimal("199.99"), 3)
        self.assertEqual(charges["base"], Decimal("599.97"))
        self.assertEqual(charges["service"], Decimal("12.00"))
        self.assertEqual(charges["gst"], Decimal("5.76"))
        self.assertEqual(charges["total"], Decimal("637.73"))
