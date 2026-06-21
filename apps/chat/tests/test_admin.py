from django.contrib.auth import get_user_model
from django.test import TransactionTestCase

from apps.chat.models import Conversation, Message
from apps.properties.models import Property

User = get_user_model()


class ConversationAdminTestCase(TransactionTestCase):
    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            email="admin@example.com", password="adminpass123"
        )
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
        Message.objects.create(
            conversation=self.conversation1,
            sender=self.user1,
            content="Message 1 in conversation 1",
        )
        Message.objects.create(
            conversation=self.conversation1,
            sender=self.user2,
            content="Message 2 in conversation 1",
        )
        Message.objects.create(
            conversation=self.conversation2,
            sender=self.user1,
            content="Message 1 in conversation 2",
        )

    def test_admin_can_view_all_conversations(self):
        self.client.force_login(self.admin_user)
        response = self.client.get("/admin/chat/conversation/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Property 1")
        self.assertContains(response, "Property 2")

    def test_admin_conversation_displays_metadata(self):
        self.client.force_login(self.admin_user)
        response = self.client.get("/admin/chat/conversation/")
        self.assertContains(response, self.user1.email)
        self.assertContains(response, self.user2.email)
        self.assertContains(response, self.user3.email)
        self.assertContains(response, self.property1.name)
        self.assertContains(response, self.property2.name)

    def test_admin_conversation_message_count(self):
        self.client.force_login(self.admin_user)
        response = self.client.get("/admin/chat/conversation/")
        content = response.content.decode()
        self.assertIn("2", content)
        self.assertIn("1", content)

    def test_admin_can_filter_by_user(self):
        self.client.force_login(self.admin_user)
        response = self.client.get(f"/admin/chat/conversation/?user={self.user2.id}")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Property 1")
        content = response.content.decode()
        self.assertIn("1\n\n    \n        Conversation", content)

    def test_admin_can_filter_by_property(self):
        self.client.force_login(self.admin_user)
        response = self.client.get(
            f"/admin/chat/conversation/?property={self.property1.id}"
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Property 1")
        content = response.content.decode()
        self.assertIn("1\n\n    \n        Conversation", content)

    def test_admin_can_search_conversations(self):
        self.client.force_login(self.admin_user)
        response = self.client.get("/admin/chat/conversation/?q=user1@example.com")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "user1@example.com")
        response = self.client.get("/admin/chat/conversation/?q=Property+1")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Property 1")


class MessageAdminTestCase(TransactionTestCase):
    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            email="admin@example.com", password="adminpass123"
        )
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
        self.conversation = Conversation.objects.create(
            property=self.property,
            participant_one=self.user1,
            participant_two=self.user2,
        )
        self.message1 = Message.objects.create(
            conversation=self.conversation,
            sender=self.user1,
            content="This is a test message from user1",
            is_read=False,
        )
        self.message2 = Message.objects.create(
            conversation=self.conversation,
            sender=self.user2,
            content="This is a test message from user2",
            is_read=True,
        )
        self.message3 = Message.objects.create(
            conversation=self.conversation,
            sender=self.user1,
            content="A" * 100,
            is_read=False,
        )

    def test_admin_can_view_all_messages(self):
        self.client.force_login(self.admin_user)
        response = self.client.get("/admin/chat/message/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "test message from user1")
        self.assertContains(response, "test message from user2")

    def test_admin_message_displays_all_fields(self):
        self.client.force_login(self.admin_user)
        response = self.client.get("/admin/chat/message/")
        self.assertContains(response, self.user1.email)
        self.assertContains(response, self.user2.email)
        self.assertContains(response, "test message from user1")
        content = response.content.decode()
        self.assertIn("is_read", content.lower())

    def test_admin_message_content_preview(self):
        self.client.force_login(self.admin_user)
        response = self.client.get("/admin/chat/message/")
        content = response.content.decode()
        self.assertNotIn("A" * 100, content)
        self.assertIn("A" * 50, content)

    def test_admin_can_filter_by_read_status(self):
        self.client.force_login(self.admin_user)
        response = self.client.get("/admin/chat/message/?is_read__exact=0")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "test message from user1")
        response = self.client.get("/admin/chat/message/?is_read__exact=1")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "test message from user2")

    def test_admin_can_search_messages(self):
        self.client.force_login(self.admin_user)
        response = self.client.get("/admin/chat/message/?q=user1@example.com")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "user1@example.com")
        response = self.client.get("/admin/chat/message/?q=test+message+from+user2")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "test message from user2")

    def test_admin_message_links_to_conversation(self):
        self.client.force_login(self.admin_user)
        response = self.client.get("/admin/chat/message/")
        self.assertContains(response, f"Conversation {self.conversation.id}")
