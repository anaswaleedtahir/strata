import re
import time
from unittest import skip

from channels.db import database_sync_to_async
from channels.testing.websocket import WebsocketCommunicator
from django.contrib.auth import get_user_model
from django.test import TransactionTestCase, override_settings

from apps.chat.consumers import ChatConsumer
from apps.chat.models import Conversation, Message
from apps.properties.models import Property

User = get_user_model()


class ConversationListViewTestCase(TransactionTestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(
            email="user1@example.com", password="testpass123"
        )
        self.user2 = User.objects.create_user(
            email="user2@example.com", password="testpass123"
        )
        self.user3 = User.objects.create_user(
            email="user3@example.com", password="testpass123"
        )
        self.property1 = Property.objects.create(
            user=self.user2,
            name="Property 1",
            full_address="123 Test St",
            property_type="House",
            description="Test property 1",
            price=100000,
        )
        self.property2 = Property.objects.create(
            user=self.user3,
            name="Property 2",
            full_address="456 Test Ave",
            property_type="Apartment",
            description="Test property 2",
            price=150000,
        )
        self.conversation1 = Conversation.objects.create(
            property=self.property1,
            participant_one=self.user1,
            participant_two=self.user2,
        )
        self.conversation2 = Conversation.objects.create(
            property=self.property2,
            participant_one=self.user1,
            participant_two=self.user3,
        )

    def test_unauthenticated_user_redirected(self):
        response = self.client.get("/chat/conversations/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/users/login/", response.url)

    def test_authenticated_user_can_access(self):
        self.client.force_login(self.user1)
        response = self.client.get("/chat/conversations/")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "chat/conversation_list.html")

    def test_user_sees_only_their_conversations(self):
        self.client.force_login(self.user1)
        response = self.client.get("/chat/conversations/")
        conversations = response.context["conversations"]
        self.assertEqual(len(conversations), 2)
        for conversation in conversations:
            self.assertTrue(
                conversation.participant_one == self.user1
                or conversation.participant_two == self.user1
            )

    def test_user_does_not_see_others_conversations(self):
        conversation3 = Conversation.objects.create(
            property=self.property1,
            participant_one=self.user2,
            participant_two=self.user3,
        )
        self.client.force_login(self.user1)
        response = self.client.get("/chat/conversations/")
        conversation_ids = [c.id for c in response.context["conversations"]]
        self.assertNotIn(conversation3.id, conversation_ids)

    def test_conversations_ordered_by_updated_at_descending(self):
        Message.objects.create(
            conversation=self.conversation1,
            sender=self.user1,
            content="Message in conversation 1",
        )
        self.conversation1.save()

        time.sleep(0.1)

        Message.objects.create(
            conversation=self.conversation2,
            sender=self.user1,
            content="Message in conversation 2",
        )
        self.conversation2.save()

        self.client.force_login(self.user1)
        response = self.client.get("/chat/conversations/")
        conversations = list(response.context["conversations"])
        self.assertEqual(conversations[0].id, self.conversation2.id)
        self.assertEqual(conversations[1].id, self.conversation1.id)

    def test_unread_message_count_accuracy(self):
        Message.objects.create(
            conversation=self.conversation1,
            sender=self.user2,
            content="Unread message 1",
            is_read=False,
        )
        Message.objects.create(
            conversation=self.conversation1,
            sender=self.user2,
            content="Unread message 2",
            is_read=False,
        )
        Message.objects.create(
            conversation=self.conversation1,
            sender=self.user2,
            content="Read message",
            is_read=True,
        )
        Message.objects.create(
            conversation=self.conversation1,
            sender=self.user1,
            content="My own message",
            is_read=False,
        )
        self.client.force_login(self.user1)
        response = self.client.get("/chat/conversations/")
        conversations = list(response.context["conversations"])
        conversation1 = next(c for c in conversations if c.id == self.conversation1.id)
        self.assertEqual(conversation1.unread_count, 2)

    def test_empty_conversation_list(self):
        user4 = User.objects.create_user(
            email="user4@example.com", password="testpass123"
        )
        self.client.force_login(user4)
        response = self.client.get("/chat/conversations/")
        conversations = response.context["conversations"]
        self.assertEqual(len(conversations), 0)
        self.assertContains(response, "No conversations yet")

    def test_other_participant_identified_correctly(self):
        self.client.force_login(self.user1)
        response = self.client.get("/chat/conversations/")
        for conversation in response.context["conversations"]:
            self.assertNotEqual(conversation.other_participant, self.user1)
            self.assertIn(
                conversation.other_participant,
                [conversation.participant_one, conversation.participant_two],
            )

    def test_conversation_displays_property_context(self):
        self.client.force_login(self.user1)
        response = self.client.get("/chat/conversations/")
        self.assertContains(response, self.property1.name)
        self.assertContains(response, self.property2.name)


class ConversationDetailViewTestCase(TransactionTestCase):
    def setUp(self):
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
            full_address="123 Test St",
            property_type="House",
            description="Test property",
            price=100000,
        )
        self.conversation = Conversation.objects.create(
            property=self.property,
            participant_one=self.user1,
            participant_two=self.user2,
        )
        self.message1 = Message.objects.create(
            conversation=self.conversation,
            sender=self.user1,
            content="First message",
            is_read=False,
        )
        self.message2 = Message.objects.create(
            conversation=self.conversation,
            sender=self.user2,
            content="Second message",
            is_read=False,
        )
        self.message3 = Message.objects.create(
            conversation=self.conversation,
            sender=self.user1,
            content="Third message",
            is_read=False,
        )

    def test_unauthenticated_user_redirected(self):
        response = self.client.get(f"/chat/conversations/{self.conversation.id}/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/users/login/", response.url)

    def test_participant_can_access_conversation(self):
        self.client.force_login(self.user1)
        response = self.client.get(f"/chat/conversations/{self.conversation.id}/")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "chat/conversation_detail.html")

    def test_non_participant_cannot_access_conversation(self):
        self.client.force_login(self.user3)
        response = self.client.get(f"/chat/conversations/{self.conversation.id}/")
        self.assertEqual(response.status_code, 403)

    def test_messages_loaded_chronologically(self):
        self.client.force_login(self.user1)
        response = self.client.get(f"/chat/conversations/{self.conversation.id}/")
        messages = list(response.context["chat_messages"])
        self.assertEqual(len(messages), 3)
        self.assertEqual(messages[0].id, self.message1.id)
        self.assertEqual(messages[1].id, self.message2.id)
        self.assertEqual(messages[2].id, self.message3.id)
        for i in range(len(messages) - 1):
            self.assertLessEqual(messages[i].created_at, messages[i + 1].created_at)

    def test_messages_marked_as_read_on_open(self):
        self.assertFalse(self.message1.is_read)
        self.assertFalse(self.message2.is_read)
        self.assertFalse(self.message3.is_read)
        self.client.force_login(self.user1)
        self.client.get(f"/chat/conversations/{self.conversation.id}/")
        self.message1.refresh_from_db()
        self.message2.refresh_from_db()
        self.message3.refresh_from_db()
        self.assertTrue(self.message2.is_read)
        self.assertFalse(self.message1.is_read)
        self.assertFalse(self.message3.is_read)

    def test_only_recipient_messages_marked_as_read(self):
        Message.objects.create(
            conversation=self.conversation,
            sender=self.user2,
            content="Message from user2 to user1",
            is_read=False,
        )
        Message.objects.create(
            conversation=self.conversation,
            sender=self.user2,
            content="Another message from user2",
            is_read=False,
        )
        self.client.force_login(self.user1)
        self.client.get(f"/chat/conversations/{self.conversation.id}/")
        unread_from_user1 = Message.objects.filter(
            conversation=self.conversation, sender=self.user1, is_read=False
        ).count()
        self.assertEqual(unread_from_user1, 2)
        unread_from_user2 = Message.objects.filter(
            conversation=self.conversation, sender=self.user2, is_read=False
        ).count()
        self.assertEqual(unread_from_user2, 0)

    def test_other_participant_identified_correctly(self):
        self.client.force_login(self.user1)
        response = self.client.get(f"/chat/conversations/{self.conversation.id}/")
        self.assertEqual(response.context["other_participant"], self.user2)

        self.client.force_login(self.user2)
        response = self.client.get(f"/chat/conversations/{self.conversation.id}/")
        self.assertEqual(response.context["other_participant"], self.user1)

    def test_conversation_context_includes_property(self):
        self.client.force_login(self.user1)
        response = self.client.get(f"/chat/conversations/{self.conversation.id}/")
        self.assertEqual(response.context["conversation"].property, self.property)
        self.assertContains(response, self.property.name)

    def test_empty_conversation_displays_correctly(self):
        empty_conversation = Conversation.objects.create(
            property=self.property,
            participant_one=self.user1,
            participant_two=self.user3,
        )
        self.client.force_login(self.user1)
        response = self.client.get(f"/chat/conversations/{empty_conversation.id}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["chat_messages"]), 0)
        self.assertContains(response, "No messages yet")

    def test_nonexistent_conversation_returns_404(self):
        self.client.force_login(self.user1)
        response = self.client.get("/chat/conversations/99999/")
        self.assertEqual(response.status_code, 404)

    def test_messages_display_sender_information(self):
        self.client.force_login(self.user1)
        response = self.client.get(f"/chat/conversations/{self.conversation.id}/")
        for message in response.context["chat_messages"]:
            self.assertIsNotNone(message.sender)
            self.assertIn(message.sender, [self.user1, self.user2])

    def test_unread_messages_highlighted_in_template(self):
        Message.objects.create(
            conversation=self.conversation,
            sender=self.user2,
            content="This is an unread message",
            is_read=False,
        )
        Message.objects.create(
            conversation=self.conversation,
            sender=self.user2,
            content="This is a read message",
            is_read=True,
        )
        self.client.force_login(self.user1)
        response = self.client.get(f"/chat/conversations/{self.conversation.id}/")
        content = response.content.decode()
        self.assertIn("ring-2 ring-ring ring-offset-2", content)
        self.assertIn("New", content)

    def test_sender_name_and_timestamp_displayed(self):
        self.client.force_login(self.user1)
        response = self.client.get(f"/chat/conversations/{self.conversation.id}/")
        content = response.content.decode()
        for message in [self.message1, self.message2, self.message3]:
            self.assertIn(message.content, content)
        timestamp_pattern = r"\w{3}\s+\d{1,2},\s+\d{4}\s+\d{1,2}:\d{2}\s+[AP]M"
        self.assertTrue(
            re.search(timestamp_pattern, content),
            "Timestamp format not found in response",
        )


class StartConversationViewTestCase(TransactionTestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(
            email="user1@example.com", password="testpass123"
        )
        self.user2 = User.objects.create_user(
            email="user2@example.com", password="testpass123"
        )
        self.property = Property.objects.create(
            user=self.user2,
            name="Test Property",
            full_address="123 Test St",
            property_type="House",
            description="Test property",
            price=100000,
        )

    def test_unauthenticated_user_redirected(self):
        response = self.client.get(f"/chat/start/{self.property.id}/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/users/login/", response.url)

    def test_property_owner_cannot_start_conversation(self):
        self.client.force_login(self.user2)
        response = self.client.get(f"/chat/start/{self.property.id}/")
        self.assertEqual(response.status_code, 403)
        self.assertIn("yourself", response.content.decode().lower())

    def test_create_new_conversation(self):
        self.client.force_login(self.user1)
        self.assertEqual(Conversation.objects.count(), 0)
        response = self.client.get(f"/chat/start/{self.property.id}/")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Conversation.objects.count(), 1)
        conversation = Conversation.objects.first()
        self.assertEqual(conversation.property, self.property)
        self.assertEqual(conversation.participant_one, self.user2)
        self.assertEqual(conversation.participant_two, self.user1)
        self.assertIn(f"/chat/conversations/{conversation.id}/", response.url)

    def test_retrieve_existing_conversation(self):
        existing_conversation = Conversation.objects.create(
            property=self.property,
            participant_one=self.user2,
            participant_two=self.user1,
        )
        self.client.force_login(self.user1)
        self.assertEqual(Conversation.objects.count(), 1)
        response = self.client.get(f"/chat/start/{self.property.id}/")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Conversation.objects.count(), 1)
        self.assertIn(f"/chat/conversations/{existing_conversation.id}/", response.url)

    def test_conversation_uniqueness_constraint(self):
        self.client.force_login(self.user1)
        response1 = self.client.get(f"/chat/start/{self.property.id}/")
        response2 = self.client.get(f"/chat/start/{self.property.id}/")
        self.assertEqual(response1.status_code, 302)
        self.assertEqual(response2.status_code, 302)
        self.assertEqual(Conversation.objects.count(), 1)
        self.assertEqual(response1.url, response2.url)

    def test_nonexistent_property_returns_404(self):
        self.client.force_login(self.user1)
        response = self.client.get("/chat/start/99999/")
        self.assertEqual(response.status_code, 404)

    def test_conversation_data_completeness(self):
        self.client.force_login(self.user1)
        self.client.get(f"/chat/start/{self.property.id}/")
        conversation = Conversation.objects.first()
        self.assertIsNotNone(conversation.property)
        self.assertIsNotNone(conversation.participant_one)
        self.assertIsNotNone(conversation.participant_two)
        self.assertIsNotNone(conversation.created_at)
        self.assertIsNotNone(conversation.updated_at)
        self.assertEqual(conversation.property.id, self.property.id)
        self.assertIn(
            self.user1, [conversation.participant_one, conversation.participant_two]
        )
        self.assertIn(
            self.user2, [conversation.participant_one, conversation.participant_two]
        )


@override_settings(
    CHANNEL_LAYERS={"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}
)
class OfflineMessageHandlingTestCase(TransactionTestCase):
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

    @database_sync_to_async
    def create_offline_messages(self):
        self.message1 = Message.objects.create(
            conversation=self.conversation,
            sender=self.user1,
            content="First offline message",
            is_read=False,
        )
        self.message2 = Message.objects.create(
            conversation=self.conversation,
            sender=self.user1,
            content="Second offline message",
            is_read=False,
        )
        self.message3 = Message.objects.create(
            conversation=self.conversation,
            sender=self.user1,
            content="Third offline message",
            is_read=False,
        )

    async def test_offline_message_persistence(self):
        await self.create_test_data()
        communicator = WebsocketCommunicator(
            ChatConsumer.as_asgi(), f"/ws/chat/{self.conversation.id}/"
        )
        communicator.scope["user"] = self.user1
        communicator.scope["url_route"] = {
            "kwargs": {"conversation_id": self.conversation.id}
        }
        connected, _ = await communicator.connect()
        self.assertTrue(connected)
        await communicator.send_json_to({"message": "Message for offline user"})
        await communicator.receive_json_from()

        @database_sync_to_async
        def check_message_status():
            message = Message.objects.filter(
                conversation=self.conversation,
                sender=self.user1,
                content="Message for offline user",
            ).first()
            return message is not None and not message.is_read

        self.assertTrue(await check_message_status())
        await communicator.disconnect()

    @skip("Unread-on-connect not implemented")
    async def test_unread_messages_delivered_on_connection(self):
        pass

    @skip("Unread-on-connect not implemented")
    async def test_only_recipient_unread_messages_delivered(self):
        pass

    @skip("Unread-on-connect not implemented")
    async def test_no_unread_messages_on_connection(self):
        pass

    def test_historical_messages_loaded_from_database(self):
        user1 = User.objects.create_user(
            email="user1@example.com", password="testpass123"
        )
        user2 = User.objects.create_user(
            email="user2@example.com", password="testpass123"
        )
        property_obj = Property.objects.create(
            user=user2,
            name="Test Property",
            full_address="123 Test St",
            property_type="House",
            description="Test property",
            price=100000,
        )
        conversation = Conversation.objects.create(
            property=property_obj,
            participant_one=user1,
            participant_two=user2,
        )
        Message.objects.create(
            conversation=conversation,
            sender=user1,
            content="Historical message 1",
            is_read=True,
        )
        Message.objects.create(
            conversation=conversation,
            sender=user2,
            content="Historical message 2",
            is_read=True,
        )
        Message.objects.create(
            conversation=conversation,
            sender=user1,
            content="Historical message 3",
            is_read=False,
        )
        self.client.force_login(user1)
        response = self.client.get(f"/chat/conversations/{conversation.id}/")
        messages = list(response.context["chat_messages"])
        self.assertEqual(len(messages), 3)
        self.assertEqual(messages[0].content, "Historical message 1")
        self.assertEqual(messages[1].content, "Historical message 2")
        self.assertEqual(messages[2].content, "Historical message 3")
        self.assertContains(response, "Historical message 1")
        self.assertContains(response, "Historical message 2")
        self.assertContains(response, "Historical message 3")

    def test_historical_messages_display_without_websocket(self):
        user1 = User.objects.create_user(
            email="user1@example.com", password="testpass123"
        )
        user2 = User.objects.create_user(
            email="user2@example.com", password="testpass123"
        )
        property_obj = Property.objects.create(
            user=user2,
            name="Test Property",
            full_address="123 Test St",
            property_type="House",
            description="Test property",
            price=100000,
        )
        conversation = Conversation.objects.create(
            property=property_obj,
            participant_one=user1,
            participant_two=user2,
        )
        Message.objects.create(
            conversation=conversation,
            sender=user1,
            content="Message without WebSocket",
            is_read=True,
        )
        self.client.force_login(user1)
        response = self.client.get(f"/chat/conversations/{conversation.id}/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Message without WebSocket")
        messages = response.context["chat_messages"]
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0].content, "Message without WebSocket")
