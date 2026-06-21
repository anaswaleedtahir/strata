from unittest.mock import AsyncMock, patch

from channels.db import database_sync_to_async
from channels.testing.websocket import WebsocketCommunicator
from django.contrib.auth import get_user_model
from django.test import TransactionTestCase, override_settings

from apps.chat.consumers import ChatConsumer
from apps.chat.models import Conversation, Message
from apps.properties.models import Property

User = get_user_model()


@override_settings(
    CHANNEL_LAYERS={"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}
)
class ChatConsumerTestCase(TransactionTestCase):
    def setUp(self):
        self.rate_limit_patcher = patch(
            "apps.chat.services.rate_limit_check",
            new=AsyncMock(return_value=(True, 0)),
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
        self.user3 = User.objects.create_user(
            email="user3@example.com", password="testpass123"
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

    def _make_communicator(self, user, conversation_id):
        communicator = WebsocketCommunicator(
            ChatConsumer.as_asgi(), f"/ws/chat/{conversation_id}/"
        )
        communicator.scope["user"] = user
        communicator.scope["url_route"] = {
            "kwargs": {"conversation_id": conversation_id}
        }
        return communicator

    async def test_authenticated_user_can_connect(self):
        await self.create_test_data()
        communicator = self._make_communicator(self.user1, self.conversation.id)
        connected, _ = await communicator.connect()
        self.assertTrue(connected)
        await communicator.disconnect()

    async def test_unauthenticated_user_cannot_connect(self):
        await self.create_test_data()
        communicator = self._make_communicator(None, self.conversation.id)
        connected, close_code = await communicator.connect()
        self.assertFalse(connected)
        self.assertEqual(close_code, 4001)

    async def test_non_participant_cannot_connect(self):
        await self.create_test_data()
        communicator = self._make_communicator(self.user3, self.conversation.id)
        connected, close_code = await communicator.connect()
        self.assertFalse(connected)
        self.assertEqual(close_code, 4003)

    async def test_send_and_receive_message(self):
        await self.create_test_data()
        communicator = self._make_communicator(self.user1, self.conversation.id)
        connected, _ = await communicator.connect()
        self.assertTrue(connected)
        await communicator.send_json_to({"message": "Hello, this is a test message"})
        response = await communicator.receive_json_from()
        self.assertEqual(response["type"], "message")
        self.assertEqual(response["message"], "Hello, this is a test message")
        self.assertEqual(response["sender_id"], self.user1.id)
        await communicator.disconnect()

    async def test_empty_message_rejected(self):
        await self.create_test_data()
        communicator = self._make_communicator(self.user1, self.conversation.id)
        connected, _ = await communicator.connect()
        self.assertTrue(connected)
        await communicator.send_json_to({"message": "   "})
        response = await communicator.receive_json_from()
        self.assertEqual(response["type"], "error")
        self.assertIn("empty", response["message"].lower())
        await communicator.disconnect()

    async def test_message_persisted_to_database(self):
        await self.create_test_data()
        communicator = self._make_communicator(self.user1, self.conversation.id)
        connected, _ = await communicator.connect()
        self.assertTrue(connected)
        test_message = "This message should be persisted"
        await communicator.send_json_to({"message": test_message})
        await communicator.receive_json_from()

        @database_sync_to_async
        def check_message():
            return Message.objects.filter(
                conversation=self.conversation, sender=self.user1, content=test_message
            ).exists()

        self.assertTrue(await check_message())
        await communicator.disconnect()

    async def test_message_length_validation(self):
        await self.create_test_data()
        communicator = self._make_communicator(self.user1, self.conversation.id)
        connected, _ = await communicator.connect()
        self.assertTrue(connected)
        await communicator.send_json_to({"message": "a" * 5001})
        response = await communicator.receive_json_from()
        self.assertEqual(response["type"], "error")
        self.assertIn("5000", response["message"])
        await communicator.disconnect()

    async def test_message_xss_sanitization(self):
        await self.create_test_data()
        communicator = self._make_communicator(self.user1, self.conversation.id)
        connected, _ = await communicator.connect()
        self.assertTrue(connected)
        await communicator.send_json_to(
            {"message": '<script>alert("XSS")</script>Hello'}
        )
        response = await communicator.receive_json_from()
        self.assertEqual(response["type"], "message")
        self.assertNotIn("<script>", response["message"])
        self.assertNotIn("</script>", response["message"])
        self.assertNotIn("alert", response["message"])
        self.assertEqual(response["message"], "Hello")
        await communicator.disconnect()

    async def test_self_messaging_prevention(self):
        await self.create_test_data()

        @database_sync_to_async
        def create_self_conversation():
            return Conversation.objects.create(
                property=self.property,
                participant_one=self.user1,
                participant_two=self.user1,
            )

        self_conversation = await create_self_conversation()
        communicator = self._make_communicator(self.user1, self_conversation.id)
        connected, _ = await communicator.connect()
        self.assertTrue(connected)
        await communicator.send_json_to({"message": "Talking to myself"})
        response = await communicator.receive_json_from()
        self.assertEqual(response["type"], "error")
        self.assertIn("yourself", response["message"].lower())
        await communicator.disconnect()

    async def test_message_at_max_length_accepted(self):
        await self.create_test_data()
        communicator = self._make_communicator(self.user1, self.conversation.id)
        connected, _ = await communicator.connect()
        self.assertTrue(connected)
        await communicator.send_json_to({"message": "a" * 5000})
        response = await communicator.receive_json_from()
        self.assertEqual(response["type"], "message")
        self.assertEqual(len(response["message"]), 5000)
        await communicator.disconnect()

    async def test_database_error_handling(self):
        await self.create_test_data()
        communicator = self._make_communicator(self.user1, self.conversation.id)
        connected, _ = await communicator.connect()
        self.assertTrue(connected)

        @database_sync_to_async
        def delete_conversation():
            Conversation.objects.filter(id=self.conversation.id).delete()

        await delete_conversation()
        with self.assertLogs("apps.chat.consumers", level="ERROR"):
            await communicator.send_json_to({"message": "This should fail to save"})
            response = await communicator.receive_json_from()
        self.assertEqual(response["type"], "error")
        self.assertIn("Failed to save message", response["message"])
        await communicator.disconnect()


@override_settings(
    CHANNEL_LAYERS={"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}
)
class MessageTypeProtocolTestCase(TransactionTestCase):
    def setUp(self):
        self.rate_limit_patcher = patch(
            "apps.chat.services.rate_limit_check",
            new=AsyncMock(return_value=(True, 0)),
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

    async def test_ping_pong_health_check(self):
        await self.create_test_data()
        communicator = self._make_communicator(self.user1)
        connected, _ = await communicator.connect()
        self.assertTrue(connected)
        await communicator.send_json_to({"type": "ping"})
        response = await communicator.receive_json_from()
        self.assertEqual(response["type"], "pong")
        await communicator.disconnect()

    async def test_backward_compatibility_no_type_field(self):
        await self.create_test_data()
        communicator = self._make_communicator(self.user1)
        connected, _ = await communicator.connect()
        self.assertTrue(connected)
        await communicator.send_json_to({"message": "Hello without type field"})
        response = await communicator.receive_json_from()
        self.assertEqual(response["type"], "message")
        self.assertEqual(response["message"], "Hello without type field")
        await communicator.disconnect()

    async def test_explicit_chat_message_type(self):
        await self.create_test_data()
        communicator = self._make_communicator(self.user1)
        connected, _ = await communicator.connect()
        self.assertTrue(connected)
        await communicator.send_json_to(
            {"type": "chat_message", "message": "Hello with explicit type"}
        )
        response = await communicator.receive_json_from()
        self.assertEqual(response["type"], "message")
        self.assertEqual(response["message"], "Hello with explicit type")
        await communicator.disconnect()

    async def test_unknown_message_type_returns_error(self):
        await self.create_test_data()
        communicator = self._make_communicator(self.user1)
        connected, _ = await communicator.connect()
        self.assertTrue(connected)
        await communicator.send_json_to({"type": "unknown_type", "data": "some data"})
        response = await communicator.receive_json_from()
        self.assertEqual(response["type"], "error")
        self.assertIn("Unknown message type", response["message"])
        await communicator.disconnect()

    async def test_ping_does_not_create_message(self):
        await self.create_test_data()
        communicator = self._make_communicator(self.user1)
        connected, _ = await communicator.connect()
        self.assertTrue(connected)

        @database_sync_to_async
        def get_message_count():
            return Message.objects.filter(conversation=self.conversation).count()

        initial_count = await get_message_count()
        await communicator.send_json_to({"type": "ping"})
        await communicator.receive_json_from()
        self.assertEqual(initial_count, await get_message_count())
        await communicator.disconnect()

    async def test_multiple_ping_pong_exchanges(self):
        await self.create_test_data()
        communicator = self._make_communicator(self.user1)
        connected, _ = await communicator.connect()
        self.assertTrue(connected)
        for _ in range(5):
            await communicator.send_json_to({"type": "ping"})
            response = await communicator.receive_json_from()
            self.assertEqual(response["type"], "pong")
        await communicator.disconnect()

    async def test_mixed_message_types(self):
        await self.create_test_data()
        communicator = self._make_communicator(self.user1)
        connected, _ = await communicator.connect()
        self.assertTrue(connected)

        await communicator.send_json_to({"type": "ping"})
        response = await communicator.receive_json_from()
        self.assertEqual(response["type"], "pong")

        await communicator.send_json_to({"type": "chat_message", "message": "Hello"})
        response = await communicator.receive_json_from()
        self.assertEqual(response["type"], "message")
        self.assertEqual(response["message"], "Hello")

        await communicator.send_json_to({"type": "ping"})
        response = await communicator.receive_json_from()
        self.assertEqual(response["type"], "pong")

        await communicator.disconnect()

    async def test_invalid_json_returns_error(self):
        await self.create_test_data()
        communicator = self._make_communicator(self.user1)
        connected, _ = await communicator.connect()
        self.assertTrue(connected)
        await communicator.send_to(text_data="invalid json {")
        response = await communicator.receive_json_from()
        self.assertEqual(response["type"], "error")
        self.assertIn("Invalid message format", response["message"])
        await communicator.disconnect()
