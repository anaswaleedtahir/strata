import random
from decimal import Decimal
from io import BytesIO

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

try:
    from PIL import Image, ImageDraw
    from faker import Faker
except ImportError as exc:  # pragma: no cover - dependency guard
    raise ImportError(
        "The seed_local command requires dev dependencies. "
        "Install them with `uv sync --group dev`."
    ) from exc

from apps.chat.models import Conversation, Message
from apps.chat.services import conversation_start, message_create
from apps.properties.models import Favorite, Property
from apps.properties.services import (
    favorite_toggle,
    property_create,
    property_image_add,
)
from apps.shared.exceptions import ApplicationError
from apps.users.services import user_create

User = get_user_model()

SEED_EMAIL_DOMAIN = "strata.local"
SEED_EMAIL_SUFFIX = f"@{SEED_EMAIL_DOMAIN}"
DEFAULT_PASSWORD = "StrataPass1!"
PROPERTY_TYPES = ("House", "Plot")
IMAGE_PALETTES = (
    ((228, 217, 201), (125, 99, 84), (181, 154, 132)),
    ((209, 224, 232), (88, 111, 125), (146, 167, 178)),
    ((223, 218, 200), (92, 96, 80), (155, 160, 134)),
    ((232, 212, 196), (132, 94, 76), (195, 150, 125)),
)
CHAT_SNIPPETS = (
    "Hi, is this property still available?",
    "Yes, it is available. Would you like to schedule a visit?",
    "That sounds good. Is there any flexibility on the price?",
    "There may be some room depending on timing and payment terms.",
    "Great, thanks. Can you share more details about the neighborhood?",
    "Absolutely. It is a quiet area with easy access to schools and shops.",
)


def seeded_user_queryset():
    return User.objects.filter(email__endswith=SEED_EMAIL_SUFFIX)


class Command(BaseCommand):
    help = "Seed local development data for Strata."

    def add_arguments(self, parser):
        parser.add_argument(
            "--users",
            type=int,
            default=8,
            help="Number of non-admin demo users to ensure.",
        )
        parser.add_argument(
            "--properties",
            type=int,
            default=12,
            help="Number of demo properties to ensure.",
        )
        parser.add_argument(
            "--favorites",
            type=int,
            default=16,
            help="Number of demo favorites to ensure.",
        )
        parser.add_argument(
            "--conversations",
            type=int,
            default=6,
            help="Number of demo conversations to ensure.",
        )
        parser.add_argument(
            "--messages",
            type=int,
            default=4,
            help="Messages to ensure per demo conversation.",
        )
        parser.add_argument(
            "--images",
            type=int,
            default=2,
            help="Images to ensure per demo property.",
        )
        parser.add_argument(
            "--password",
            default=DEFAULT_PASSWORD,
            help="Password assigned to every seeded user.",
        )
        parser.add_argument(
            "--random-seed",
            type=int,
            default=42,
            help="Random seed used for repeatable local data.",
        )
        parser.add_argument(
            "--reset",
            action="store_true",
            help=f"Delete existing {SEED_EMAIL_SUFFIX} seed users before seeding.",
        )
        parser.add_argument(
            "--delete",
            action="store_true",
            help=f"Delete existing {SEED_EMAIL_SUFFIX} seed users and exit.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        self._validate_counts(options)
        random.seed(options["random_seed"])
        fake = Faker()
        Faker.seed(options["random_seed"])
        self._images_per_property = options["images"]

        if options["reset"]:
            deleted = self._reset_seed_data()
            self.stdout.write(f"Deleted {deleted} existing seeded user(s).")

        if options["delete"]:
            deleted = self._reset_seed_data()
            self.stdout.write(
                self.style.SUCCESS(f"Deleted {deleted} existing seeded user(s).")
            )
            return

        admin = self._ensure_user(
            email=f"admin{SEED_EMAIL_SUFFIX}",
            first_name="Strata",
            last_name="Admin",
            password=options["password"],
            is_superuser=True,
        )
        users = self._ensure_users(
            count=options["users"],
            password=options["password"],
            fake=fake,
        )
        properties = self._ensure_properties(
            count=options["properties"],
            owners=users[: max(1, len(users) // 3)] or [admin],
            fake=fake,
        )
        favorites_created = self._ensure_favorites(
            count=options["favorites"],
            users=users,
            properties=properties,
        )
        conversations = self._ensure_conversations(
            count=options["conversations"],
            users=users,
            properties=properties,
        )
        messages_created = self._ensure_messages(
            conversations=conversations,
            messages_per_conversation=options["messages"],
        )

        self.stdout.write(
            self.style.SUCCESS(
                "Seeded local data: "
                f"users={len(users) + 1}, "
                f"properties={len(properties)}, "
                f"favorites={Favorite.objects.filter(user__email__endswith=SEED_EMAIL_SUFFIX).count()} "
                f"(created {favorites_created}), "
                f"conversations={len(conversations)}, "
                f"messages={Message.objects.filter(conversation__in=conversations).count()} "
                f"(created {messages_created})"
            )
        )

    def _validate_counts(self, options):
        count_options = (
            "users",
            "properties",
            "favorites",
            "conversations",
            "messages",
            "images",
        )
        for option_name in count_options:
            if options[option_name] < 0:
                raise CommandError(f"--{option_name.replace('_', '-')} must be >= 0.")

    def _reset_seed_data(self):
        queryset = seeded_user_queryset()
        count = queryset.count()
        queryset.delete()
        return count

    def _ensure_users(self, *, count, password, fake):
        return [
            self._ensure_user(
                email=f"user{index}{SEED_EMAIL_SUFFIX}",
                first_name=fake.first_name(),
                last_name=fake.last_name(),
                password=password,
            )
            for index in range(1, count + 1)
        ]

    def _ensure_user(
        self,
        *,
        email,
        first_name,
        last_name,
        password,
        is_superuser=False,
    ):
        user = User.objects.filter(email=email).first()
        if user is None:
            try:
                user = user_create(
                    email=email,
                    password=password,
                    first_name=first_name,
                    last_name=last_name,
                )
            except ApplicationError as exc:
                raise CommandError(exc.message) from exc
        else:
            user.first_name = first_name
            user.last_name = last_name
            user.set_password(password)

        user.is_superuser = is_superuser
        user.full_clean()
        user.save()
        return user

    def _ensure_properties(self, *, count, owners, fake):
        properties = list(
            Property.objects.filter(
                user__email__endswith=SEED_EMAIL_SUFFIX,
                name__startswith="Seed Property ",
            ).order_by("id")[:count]
        )

        for index in range(len(properties) + 1, count + 1):
            owner = owners[(index - 1) % len(owners)]
            property_type = random.choice(PROPERTY_TYPES)
            bedrooms = random.randint(1, 5) if property_type == "House" else None
            bathrooms = random.randint(1, 4) if property_type == "House" else None
            form_data = {
                "name": f"Seed Property {index}",
                "description": fake.paragraph(nb_sentences=4),
                "full_address": fake.address().replace("\n", ", ")[:255],
                "phone_number": f"+92-{random.randint(3000000000, 3499999999)}",
                "cnic": (
                    f"{random.randint(10000, 99999)}-"
                    f"{random.randint(1000000, 9999999)}-"
                    f"{random.randint(0, 9)}"
                ),
                "property_type": property_type,
                "price": Decimal(random.randrange(7500000, 75000000, 50000)),
                "bedrooms": bedrooms,
                "bathrooms": bathrooms,
                "area": Decimal(random.randrange(600, 5000)),
                "documents": None,
                "is_published": random.random() > 0.15,
            }
            images = [
                self._generate_property_image(
                    property_index=index, image_index=image_index
                )
                for image_index in range(1, self._images_per_property + 1)
            ]
            try:
                properties.append(
                    property_create(user=owner, form_data=form_data, images=images)
                )
            except ApplicationError as exc:
                raise CommandError(exc.message) from exc

        for property_obj in properties:
            self._ensure_property_images(property_obj=property_obj)

        return properties

    def _ensure_property_images(self, *, property_obj):
        missing_images = max(0, self._images_per_property - property_obj.images.count())
        for offset in range(1, missing_images + 1):
            image = self._generate_property_image(
                property_index=property_obj.id,
                image_index=property_obj.images.count() + offset,
            )
            property_image_add(
                property_obj=property_obj,
                image_file=image,
                is_primary=(property_obj.images.count() == 0),
            )

    def _generate_property_image(self, *, property_index, image_index):
        width, height = 1200, 800
        background, secondary, accent = random.choice(IMAGE_PALETTES)
        image = Image.new("RGB", (width, height), color=background)
        draw = ImageDraw.Draw(image)
        horizon = 430

        draw.rectangle((0, 0, width, horizon), fill=background)
        draw.polygon(((220, horizon), (600, 180), (980, horizon)), fill=accent)
        draw.rectangle((315, horizon - 20, 885, 625), fill=(246, 242, 232))
        draw.rectangle((395, 420, 520, 625), fill=secondary)
        draw.rectangle((610, 410, 795, 525), fill=(178, 204, 216))
        draw.rectangle((630, 430, 775, 505), outline=(80, 92, 96), width=6)
        draw.rectangle((0, 625, width, height), fill=(184, 189, 170))

        buffer = BytesIO()
        image.save(buffer, format="JPEG", quality=82)
        buffer.seek(0)
        return SimpleUploadedFile(
            name=f"seed-property-{property_index}-{image_index}.jpg",
            content=buffer.read(),
            content_type="image/jpeg",
        )

    def _ensure_favorites(self, *, count, users, properties):
        if not users or not properties:
            return 0

        created = 0
        attempts = 0
        max_attempts = max(count * 10, 25)
        while (
            Favorite.objects.filter(user__email__endswith=SEED_EMAIL_SUFFIX).count()
            < count
            and attempts < max_attempts
        ):
            attempts += 1
            user = random.choice(users)
            property_obj = random.choice(properties)
            if property_obj.user_id == user.id:
                continue
            if Favorite.objects.filter(user=user, property=property_obj).exists():
                continue
            favorite_toggle(user=user, property_obj=property_obj)
            created += 1
        return created

    def _ensure_conversations(self, *, count, users, properties):
        if not users or not properties:
            return []

        conversations = list(
            Conversation.objects.filter(
                participant_one__email__endswith=SEED_EMAIL_SUFFIX,
                participant_two__email__endswith=SEED_EMAIL_SUFFIX,
            ).order_by("id")[:count]
        )
        attempts = 0
        max_attempts = max(count * 10, 25)
        while len(conversations) < count and attempts < max_attempts:
            attempts += 1
            property_obj = random.choice(properties)
            candidates = [user for user in users if user.id != property_obj.user_id]
            if not candidates:
                continue
            user = random.choice(candidates)
            try:
                conversation = conversation_start(user=user, property_obj=property_obj)
            except ApplicationError:
                continue
            if conversation not in conversations:
                conversations.append(conversation)
        return conversations

    def _ensure_messages(self, *, conversations, messages_per_conversation):
        created = 0
        for conversation in conversations:
            existing_count = conversation.messages.count()
            missing_count = max(0, messages_per_conversation - existing_count)
            participants = (
                conversation.participant_one,
                conversation.participant_two,
            )
            for index in range(missing_count):
                sender = participants[(existing_count + index) % 2]
                content = CHAT_SNIPPETS[(existing_count + index) % len(CHAT_SNIPPETS)]
                message_create(
                    conversation=conversation,
                    sender=sender,
                    content=content,
                )
                created += 1

            Message.objects.filter(conversation=conversation).exclude(
                sender=conversation.participant_two
            ).update(is_read=True)

        return created
