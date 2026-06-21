from unittest.mock import AsyncMock, patch

from channels.db import database_sync_to_async
from channels.testing.websocket import WebsocketCommunicator
from django.contrib.auth import get_user_model
from django.test import TransactionTestCase, override_settings

from apps.chat import services
from apps.chat.consumers import ChatConsumer
from apps.chat.models import Conversation, Message
from apps.properties.models import Property
from apps.shared.exceptions import ApplicationError

User = get_user_model()


@override_settings(
    CHANNEL_LAYERS={"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}
)
class RateLimitingTestCase(TransactionTestCase):
    def setUp(self):
        self.rate_limit_calls = 0

        async def fake_rate_limit_check(*, user_id, redis_url):
            self.rate_limit_calls += 1
            if self.rate_limit_calls <= 10:
                return True, 0
            return False, 42

        self.rate_limit_patcher = patch(
            "apps.chat.services.rate_limit_check", side_effect=fake_rate_limit_check
        )
        self.rate_limit_patcher.start()
        self.addCleanup(self.rate_limit_patcher.stop)

    @database_sync_to_async
    def create_test_data(self):
        self.user1 = User.objects.create_user(
            email="user1@example.com", password="testpass123"
        )
        self.user2 = User.objects.create_user(
            email="user2@example.com", password="testpass123"
        )
        self.property = Property.objects.create(
            user=self.user2,
            name="Test Property",
            full_address="123 Test St, Test City, TS 12345",
            property_type="House",
            description="A test property",
            price=100000,
        )
        self.conversation = Conversation.objects.create(
            property=self.property,
            participant_one=self.user1,
            participant_two=self.user2,
        )

    def _make_communicator(self, user):
        communicator = WebsocketCommunicator(
            ChatConsumer.as_asgi(), f"/ws/chat/{self.conversation.id}/"
        )
        communicator.scope["user"] = user
        communicator.scope["url_route"] = {
            "kwargs": {"conversation_id": self.conversation.id}
        }
        return communicator

    async def test_rate_limit_allows_messages_within_limit(self):
        await self.create_test_data()
        communicator = self._make_communicator(self.user1)
        connected, _ = await communicator.connect()
        self.assertTrue(connected)
        for i in range(10):
            await communicator.send_json_to({"message": f"Message {i + 1}"})
            response = await communicator.receive_json_from()
            self.assertEqual(response["type"], "message")
            self.assertEqual(response["message"], f"Message {i + 1}")
        await communicator.disconnect()

    async def test_rate_limit_blocks_excess_messages(self):
        await self.create_test_data()
        communicator = self._make_communicator(self.user1)
        connected, _ = await communicator.connect()
        self.assertTrue(connected)
        for i in range(10):
            await communicator.send_json_to({"message": f"Message {i + 1}"})
            await communicator.receive_json_from()
        await communicator.send_json_to({"message": "Message 11 - should be blocked"})
        response = await communicator.receive_json_from()
        self.assertEqual(response["type"], "rate_limit_error")
        self.assertEqual(response["status_code"], 429)
        self.assertIn("Rate limit exceeded", response["message"])
        self.assertIn("cooldown_seconds", response)
        self.assertGreater(response["cooldown_seconds"], 0)
        await communicator.disconnect()

    async def test_rate_limit_cooldown_calculation(self):
        await self.create_test_data()
        communicator = self._make_communicator(self.user1)
        connected, _ = await communicator.connect()
        self.assertTrue(connected)
        for i in range(10):
            await communicator.send_json_to({"message": f"Message {i + 1}"})
            await communicator.receive_json_from()
        await communicator.send_json_to({"message": "Blocked message"})
        response = await communicator.receive_json_from()
        cooldown = response["cooldown_seconds"]
        self.assertGreater(cooldown, 0)
        self.assertLessEqual(cooldown, 61)
        await communicator.disconnect()

    async def test_rate_limit_message_not_persisted(self):
        await self.create_test_data()
        communicator = self._make_communicator(self.user1)
        connected, _ = await communicator.connect()
        self.assertTrue(connected)
        for i in range(10):
            await communicator.send_json_to({"message": f"Message {i + 1}"})
            await communicator.receive_json_from()
        await communicator.send_json_to({"message": "Blocked message"})
        response = await communicator.receive_json_from()
        self.assertEqual(response["type"], "rate_limit_error")

        @database_sync_to_async
        def check_message_count():
            return Message.objects.filter(conversation=self.conversation).count()

        self.assertEqual(await check_message_count(), 10)
        await communicator.disconnect()


class MessageDeliveryTestCase(TransactionTestCase):
    @database_sync_to_async
    def create_test_data(self):
        self.user1 = User.objects.create_user(
            email="user1@example.com", password="testpass123"
        )
        self.user2 = User.objects.create_user(
            email="user2@example.com", password="testpass123"
        )
        self.property = Property.objects.create(
            user=self.user2,
            name="Test Property",
            full_address="123 Test St, Test City, TS 12345",
            property_type="House",
            description="A test property",
            price=100000,
        )
        self.conversation = Conversation.objects.create(
            property=self.property,
            participant_one=self.user1,
            participant_two=self.user2,
        )

    async def test_rejects_empty_message_without_persisting(self):
        await self.create_test_data()

        with self.assertRaisesMessage(
            ApplicationError, "Message content cannot be empty"
        ):
            await services.message_deliver(
                conversation=self.conversation,
                sender=self.user1,
                content="   ",
                redis_url="redis://unused",
            )

        @database_sync_to_async
        def message_count():
            return Message.objects.filter(conversation=self.conversation).count()

        self.assertEqual(await message_count(), 0)

    async def test_delivers_sanitized_message_with_transport_neutral_payload(self):
        await self.create_test_data()

        with patch.object(
            services, "rate_limit_check", new=AsyncMock(return_value=(True, 0))
        ):
            message = await services.message_deliver(
                conversation=self.conversation,
                sender=self.user1,
                content='<script>alert("XSS")</script>Hello',
                redis_url="redis://unused",
            )

        self.assertEqual(message.content, "Hello")


class ConversationStartTestCase(TransactionTestCase):
    def test_rejects_unpublished_property(self):
        owner = User.objects.create_user(
            email="owner@example.com", password="testpass123"
        )
        participant = User.objects.create_user(
            email="participant@example.com", password="testpass123"
        )
        property_obj = Property.objects.create(
            user=owner,
            name="Draft Property",
            full_address="123 Test St, Test City, TS 12345",
            property_type="House",
            description="A draft property",
            price=100000,
            is_published=False,
        )

        with self.assertRaisesMessage(ApplicationError, "Property is not available."):
            services.conversation_start(user=participant, property_obj=property_obj)

        self.assertEqual(Conversation.objects.count(), 0)
