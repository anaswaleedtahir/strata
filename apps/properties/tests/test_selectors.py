from django.test import TestCase

from apps.properties.selectors import property_list_published
from apps.properties.tests.factories import PropertyFactory


class PropertyListPublishedTests(TestCase):
    def test_searches_name_address_and_description(self):
        matching_name = PropertyFactory(name="Canal View House")
        matching_address = PropertyFactory(full_address="Canal Road, Lahore")
        matching_description = PropertyFactory(description="Near the canal")
        PropertyFactory(name="Mountain cabin", full_address="Murree")

        result = list(property_list_published(query="canal"))

        self.assertCountEqual(
            result, [matching_name, matching_address, matching_description]
        )

    def test_filters_property_attributes(self):
        match = PropertyFactory(
            property_type="House",
            price="15000000",
            bedrooms=3,
            bathrooms=2,
        )
        PropertyFactory(property_type="Plot", price="12000000")
        PropertyFactory(
            property_type="House",
            price="30000000",
            bedrooms=2,
            bathrooms=1,
        )

        result = list(
            property_list_published(
                property_type="House",
                min_price="10000000",
                max_price="20000000",
                bedrooms=3,
                bathrooms=2,
            )
        )

        self.assertEqual(result, [match])

    def test_orders_by_price(self):
        expensive = PropertyFactory(price="30000000")
        affordable = PropertyFactory(price="10000000")

        ascending = list(property_list_published(ordering="price_asc"))
        descending = list(property_list_published(ordering="price_desc"))

        self.assertEqual(ascending, [affordable, expensive])
        self.assertEqual(descending, [expensive, affordable])

    def test_excludes_unpublished_properties(self):
        published = PropertyFactory(is_published=True)
        PropertyFactory(is_published=False)

        self.assertEqual(list(property_list_published()), [published])
