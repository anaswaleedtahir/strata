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
