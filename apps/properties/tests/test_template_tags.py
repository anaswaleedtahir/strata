from django.test import SimpleTestCase

from apps.properties.templatetags.property_tags import pkr, pkr_compact


class PropertyPriceFormattingTests(SimpleTestCase):
    def test_formats_full_pkr_price(self):
        self.assertEqual(pkr("14250000.00"), "PKR 14,250,000")

    def test_formats_compact_pkr_price(self):
        self.assertEqual(pkr_compact("14250000.00"), "PKR 14.25M")

    def test_handles_missing_value(self):
        self.assertEqual(pkr(None), "PKR —")
