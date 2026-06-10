from django.conf import settings
from django.test import SimpleTestCase
from django.urls import reverse


class DjangoIntegrationSettingsTests(SimpleTestCase):
    def test_htmx_allauth_and_widget_tweaks_are_configured(self):
        expected_apps = {
            "django_htmx",
            "widget_tweaks",
            "django.contrib.sites",
            "allauth",
            "allauth.account",
        }

        self.assertTrue(expected_apps.issubset(set(settings.INSTALLED_APPS)))
        self.assertIn("django_htmx.middleware.HtmxMiddleware", settings.MIDDLEWARE)
        self.assertIn(
            "allauth.account.middleware.AccountMiddleware", settings.MIDDLEWARE
        )
        self.assertIn(
            "allauth.account.auth_backends.AuthenticationBackend",
            settings.AUTHENTICATION_BACKENDS,
        )
        self.assertEqual(settings.ACCOUNT_LOGIN_METHODS, {"email"})
        self.assertEqual(
            settings.ACCOUNT_SIGNUP_FIELDS,
            ["email*", "password1*", "password2*"],
        )

    def test_allauth_urls_are_mounted(self):
        self.assertEqual(reverse("account_login"), "/accounts/login/")
