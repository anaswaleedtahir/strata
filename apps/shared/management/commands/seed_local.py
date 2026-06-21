from datetime import timedelta

from allauth.account.models import EmailAddress
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.chat.models import Conversation, Message
from apps.properties.models import Favorite, Property


class Command(BaseCommand):
    help = "Load local demo data."

    @transaction.atomic
    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("Seed data is only available in DEBUG mode.")

        User = get_user_model()
        if any(
            model.objects.exists()
            for model in (User, Property, Favorite, Conversation, Message)
        ):
            raise CommandError("Seed data requires an empty database.")

        call_command("loaddata", "seed_local")

        now = timezone.now()
        User.objects.update(date_joined=now - timedelta(days=7))
        Property.objects.update(
            created_at=now - timedelta(days=2), updated_at=now - timedelta(days=2)
        )
        Favorite.objects.update(
            created_at=now - timedelta(hours=12), updated_at=now - timedelta(hours=12)
        )
        Conversation.objects.update(
            created_at=now - timedelta(minutes=30),
            updated_at=now - timedelta(minutes=5),
        )
        for minutes, message in zip((10, 5), Message.objects.order_by("pk")):
            Message.objects.filter(pk=message.pk).update(
                created_at=now - timedelta(minutes=minutes)
            )

        for user in User.objects.all():
            EmailAddress.objects.create(
                user=user, email=user.email, primary=True, verified=True
            )

        for model in (User, Property, Favorite, Conversation, Message, EmailAddress):
            for obj in model.objects.all():
                obj.full_clean()

        self.stdout.write(self.style.SUCCESS("Loaded local demo data."))
