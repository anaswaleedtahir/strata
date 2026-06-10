from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


User = get_user_model()


class AllauthSignupTests(TestCase):
    def _signup_data(self, **overrides):
        data = {
            "email": "NEW.USER@EXAMPLE.COM",
            "first_name": "New",
            "last_name": "User",
            "password1": "StrongPass1!",
            "password2": "StrongPass1!",
        }
        data.update(overrides)
        return data

    def test_missing_first_name_does_not_create_user(self):
        response = self.client.post(
            reverse("account_signup"), self._signup_data(first_name="")
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(User.objects.count(), 0)
        self.assertFormError(
            response.context["form"], "first_name", "First name is required."
        )

    def test_missing_last_name_does_not_create_user(self):
        response = self.client.post(
            reverse("account_signup"), self._signup_data(last_name="")
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(User.objects.count(), 0)
        self.assertFormError(
            response.context["form"], "last_name", "Last name is required."
        )

    def test_weak_password_does_not_create_user(self):
        response = self.client.post(
            reverse("account_signup"),
            self._signup_data(password1="password", password2="password"),
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(User.objects.count(), 0)
        self.assertFormError(
            response.context["form"],
            "password1",
            "Password must contain at least one digit.",
        )

    def test_valid_signup_creates_user_with_normalized_profile_fields(self):
        response = self.client.post(reverse("account_signup"), self._signup_data())

        self.assertRedirects(response, reverse("properties:list"))
        user = User.objects.get()
        self.assertEqual(user.email, "new.user@example.com")
        self.assertEqual(user.first_name, "New")
        self.assertEqual(user.last_name, "User")
        self.assertTrue(user.check_password("StrongPass1!"))
