from io import StringIO
from tempfile import TemporaryDirectory

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings

from apps.chat.models import Conversation, Message
from apps.properties.models import Favorite, Property, PropertyImage

User = get_user_model()


class SeedLocalCommandTests(TestCase):
    def setUp(self):
        self.media_root = TemporaryDirectory()
        self.override = override_settings(MEDIA_ROOT=self.media_root.name)
        self.override.enable()
        self.addCleanup(self.override.disable)
        self.addCleanup(self.media_root.cleanup)

    def test_seeds_local_data(self):
        stdout = StringIO()

        call_command(
            "seed_local",
            users=3,
            properties=4,
            favorites=2,
            conversations=2,
            messages=2,
            images=2,
            stdout=stdout,
        )

        self.assertIn("Seeded local data", stdout.getvalue())
        self.assertEqual(User.objects.filter(email__endswith="strata.local").count(), 4)
        self.assertEqual(Property.objects.count(), 4)
        self.assertEqual(Favorite.objects.count(), 2)
        self.assertEqual(Conversation.objects.count(), 2)
        self.assertEqual(Message.objects.count(), 4)
        self.assertEqual(PropertyImage.objects.count(), 8)
        self.assertEqual(
            PropertyImage.objects.filter(is_primary=True).count(),
            4,
        )

    def test_reset_only_deletes_seed_users(self):
        User.objects.create_user(
            email="real@example.com",
            password="TestPass1!",
            first_name="Real",
            last_name="User",
        )
        call_command(
            "seed_local",
            users=2,
            properties=2,
            conversations=1,
            messages=1,
            images=1,
            reset=True,
            stdout=StringIO(),
        )

        self.assertTrue(User.objects.filter(email="real@example.com").exists())
        self.assertEqual(User.objects.filter(email__endswith="strata.local").count(), 3)

    def test_delete_removes_seed_data_without_reseeding(self):
        User.objects.create_user(
            email="real@example.com",
            password="TestPass1!",
            first_name="Real",
            last_name="User",
        )
        call_command(
            "seed_local",
            users=2,
            properties=2,
            images=1,
            stdout=StringIO(),
        )

        stdout = StringIO()
        call_command("seed_local", delete=True, stdout=stdout)

        self.assertIn("Deleted 3 existing seeded user(s).", stdout.getvalue())
        self.assertTrue(User.objects.filter(email="real@example.com").exists())
        self.assertFalse(User.objects.filter(email__endswith="strata.local").exists())
        self.assertFalse(Property.objects.exists())
        self.assertFalse(PropertyImage.objects.exists())

    def test_reset_and_delete_cannot_be_combined(self):
        with self.assertRaisesMessage(
            CommandError,
            "Use either --reset or --delete, not both.",
        ):
            call_command("seed_local", reset=True, delete=True, stdout=StringIO())
