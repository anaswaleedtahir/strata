from django.test import TestCase
from django.urls import reverse


class LoginViewTests(TestCase):
    def test_login_page_renders(self):
        response = self.client.get(reverse("users:login"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Email")
