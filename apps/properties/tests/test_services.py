from django.test import TestCase

from apps.properties.services import favorite_toggle, property_create, property_delete
from apps.properties.tests.factories import FavoriteFactory, PropertyFactory
from apps.shared.tests.factories import UserFactory


class PropertyCreateTests(TestCase):
    def setUp(self):
        self.user = UserFactory()
        self.form_data = {
            "name": "Test House",
            "description": "Nice place",
            "full_address": "123 Main St",
            "property_type": "House",
            "price": "5000000.00",
            "bedrooms": 3,
            "bathrooms": 2,
            "area": "1200.00",
            "documents": None,
            "is_published": True,
        }

    def test_creates_property(self):
        prop = property_create(user=self.user, form_data=self.form_data, images=[])
        self.assertEqual(prop.name, "Test House")
        self.assertEqual(prop.user, self.user)

    def test_property_has_timestamps(self):
        prop = property_create(user=self.user, form_data=self.form_data, images=[])
        self.assertIsNotNone(prop.created_at)
        self.assertIsNotNone(prop.updated_at)


class PropertyDeleteTests(TestCase):
    def test_deletes_property(self):
        prop = PropertyFactory()
        pk = prop.pk
        property_delete(property_obj=prop)
        from apps.properties.models import Property

        self.assertFalse(Property.objects.filter(pk=pk).exists())


class FavoriteToggleTests(TestCase):
    def test_adds_favorite(self):
        user = UserFactory()
        prop = PropertyFactory()
        result = favorite_toggle(user=user, property_obj=prop)
        self.assertTrue(result)

    def test_removes_favorite(self):
        fav = FavoriteFactory()
        result = favorite_toggle(user=fav.user, property_obj=fav.property)
        self.assertFalse(result)

    def test_toggle_twice_removes_then_adds(self):
        user = UserFactory()
        prop = PropertyFactory()
        favorite_toggle(user=user, property_obj=prop)
        favorite_toggle(user=user, property_obj=prop)
        result = favorite_toggle(user=user, property_obj=prop)
        self.assertTrue(result)
