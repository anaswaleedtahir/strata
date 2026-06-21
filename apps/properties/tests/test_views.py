import json

from django.test import TestCase
from django.urls import reverse

from apps.properties.tests.factories import PropertyFactory
from apps.shared.tests.factories import UserFactory


class PropertyFavoriteToggleViewTests(TestCase):
    def test_htmx_toggle_returns_favorite_event(self):
        user = UserFactory()
        property_obj = PropertyFactory()
        self.client.force_login(user)

        response = self.client.post(
            reverse("properties:favorite_toggle", args=[property_obj.pk]),
            HTTP_HX_REQUEST="true",
        )

        self.assertEqual(response.status_code, 200)
        event = json.loads(response["HX-Trigger"])
        self.assertEqual(
            event,
            {
                "favorite-toggled": {
                    "propertyId": property_obj.pk,
                    "isFavorited": True,
                }
            },
        )


class PropertyListViewTests(TestCase):
    def test_applies_discovery_filters(self):
        matching = PropertyFactory(
            name="Lahore family home",
            property_type="House",
            price="18000000",
            bedrooms=3,
        )
        PropertyFactory(
            name="Karachi family home",
            property_type="House",
            price="28000000",
            bedrooms=3,
        )

        response = self.client.get(
            reverse("properties:list"),
            {
                "q": "Lahore",
                "property_type": "House",
                "max_price": "20000000",
                "bedrooms": "3",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context["properties"]), [matching])

    def test_invalid_price_range_is_shown_on_filter_form(self):
        response = self.client.get(
            reverse("properties:list"),
            {"min_price": "20000000", "max_price": "10000000"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response.context["filter_form"],
            "max_price",
            "Maximum price must be at least the minimum.",
        )
