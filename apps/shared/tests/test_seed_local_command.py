from django.core.management import call_command
from django.test import TestCase

from apps.chat.services import conversation_start, message_create
from apps.properties.models import Favorite, Property
from apps.properties.services import favorite_toggle, property_create
from apps.shared.management.commands.seed_local import (
    SEED_EMAIL_SUFFIX,
    seeded_user_queryset,
)
from apps.shared.tests.factories import UserFactory


class SeedLocalCommandTests(TestCase):
    def test_seeded_user_queryset_matches_only_exact_seed_suffix(self):
        seeded_user = UserFactory(email=f"user1{SEED_EMAIL_SUFFIX}")
        lookalike_users = [
            UserFactory(email="user@notstrata.local"),
            UserFactory(email="user@dev.strata.local"),
        ]

        queryset_ids = set(seeded_user_queryset().values_list("id", flat=True))

        self.assertEqual(queryset_ids, {seeded_user.id})
        self.assertTrue(all(user.id not in queryset_ids for user in lookalike_users))

    def test_delete_only_removes_exact_seed_users_and_their_related_data(self):
        seeded_owner = UserFactory(email=f"owner{SEED_EMAIL_SUFFIX}")
        seeded_guest = UserFactory(email=f"guest{SEED_EMAIL_SUFFIX}")
        lookalike_owner = UserFactory(email="owner@dev.strata.local")
        lookalike_guest = UserFactory(email="guest@notstrata.local")

        seeded_property = self._create_property(seeded_owner, "Seeded Listing")
        lookalike_property = self._create_property(lookalike_owner, "Lookalike Listing")

        favorite_toggle(user=seeded_guest, property_obj=seeded_property)
        favorite_toggle(user=lookalike_guest, property_obj=lookalike_property)

        seeded_conversation = conversation_start(
            user=seeded_guest,
            property_obj=seeded_property,
        )
        message_create(
            conversation=seeded_conversation,
            sender=seeded_guest,
            content="seeded message",
        )

        lookalike_conversation = conversation_start(
            user=lookalike_guest,
            property_obj=lookalike_property,
        )
        message_create(
            conversation=lookalike_conversation,
            sender=lookalike_guest,
            content="lookalike message",
        )

        call_command("seed_local", delete=True)

        self.assertFalse(type(seeded_owner).objects.filter(id=seeded_owner.id).exists())
        self.assertFalse(type(seeded_guest).objects.filter(id=seeded_guest.id).exists())
        self.assertTrue(
            type(lookalike_owner).objects.filter(id=lookalike_owner.id).exists()
        )
        self.assertTrue(
            type(lookalike_guest).objects.filter(id=lookalike_guest.id).exists()
        )
        self.assertFalse(Property.objects.filter(id=seeded_property.id).exists())
        self.assertTrue(Property.objects.filter(id=lookalike_property.id).exists())
        self.assertEqual(Favorite.objects.count(), 1)
        self.assertEqual(Property.objects.count(), 1)

    def _create_property(self, user, name):
        return property_create(
            user=user,
            form_data={
                "name": name,
                "description": "A nice place",
                "full_address": "123 Test Street",
                "property_type": "House",
                "price": "10000000.00",
                "bedrooms": 3,
                "bathrooms": 2,
                "area": "1200.00",
                "documents": None,
                "is_published": True,
            },
            images=[],
        )
