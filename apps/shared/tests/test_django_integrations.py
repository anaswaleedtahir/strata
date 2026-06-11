from django.conf import settings
from django.test import SimpleTestCase
from django.urls import reverse


class DjangoIntegrationSettingsTests(SimpleTestCase):
    def test_cotton_and_tailwind_cli_are_configured(self):
        self.assertIn("django_cotton", settings.INSTALLED_APPS)
        self.assertIn("django_tailwind_cli", settings.INSTALLED_APPS)
        self.assertEqual(settings.TAILWIND_CLI_SRC_CSS, "assets/css/input.css")
        self.assertEqual(settings.TAILWIND_CLI_DIST_CSS, "dist/output.css")
        self.assertTrue(settings.TAILWIND_CLI_USE_DAISY_UI)
        self.assertEqual(settings.TAILWIND_CLI_VERSION, "2.8.3")

    def test_base_template_uses_tailwind_cli_and_pinned_cdn_assets(self):
        base_template = (settings.BASE_DIR / "templates/_layouts/base.html").read_text()

        self.assertIn("{% load static tailwind_cli %}", base_template)
        self.assertIn("{% tailwind_css %}", base_template)
        self.assertIn(
            "https://cdn.jsdelivr.net/npm/htmx.org@1.9.10/dist/htmx.min.js",
            base_template,
        )
        self.assertIn(
            "sha384-D1Kt99CQMDuVetoL1lrYwg5t+9QdHe7NLX/SoJYkXDFfX37iInKRy5xLSi8nO7UC",
            base_template,
        )
        self.assertIn(
            "https://cdn.jsdelivr.net/npm/alpinejs@3.13.3/dist/cdn.min.js",
            base_template,
        )
        self.assertIn(
            "sha384-Rpe/8orFUm5Q1GplYBHxbuA8Az8O8C5sAoOsdbRWkqPjKFaxPgGZipj4zeHL7lxX",
            base_template,
        )

    def test_tailwind_source_file_exists_outside_staticfiles_dirs(self):
        source_path = settings.BASE_DIR / settings.TAILWIND_CLI_SRC_CSS

        self.assertTrue(source_path.exists())
        self.assertNotIn(settings.BASE_DIR / "assets", settings.STATICFILES_DIRS)
        self.assertEqual(settings.STATICFILES_DIRS, [settings.BASE_DIR / "static"])

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
            ["email*", "first_name*", "last_name*", "password1*", "password2*"],
        )
        self.assertEqual(
            settings.ACCOUNT_FORMS["signup"], "apps.users.forms.AllauthSignupForm"
        )
        self.assertEqual(
            settings.ACCOUNT_ADAPTER, "apps.users.adapters.PropertyHubAccountAdapter"
        )

    def test_allauth_urls_are_mounted(self):
        self.assertEqual(reverse("account_login"), "/accounts/login/")
