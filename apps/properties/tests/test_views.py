import json
from pathlib import Path

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from apps.properties.tests.factories import PropertyFactory
from apps.shared.tests.factories import UserFactory


class PropertyFavoriteToggleViewTests(TestCase):
    def test_htmx_toggle_returns_favorite_event(self):
        user = UserFactory()
        property_obj = PropertyFactory()
        self.client.force_login(user)

        response = self.client.post(
            reverse("properties:favorite_toggle", args=[property_obj.pk]),
            HTTP_HX_REQUEST="true",
        )

        self.assertEqual(response.status_code, 200)
        event = json.loads(response["HX-Trigger"])
        self.assertEqual(
            event,
            {
                "favorite-toggled": {
                    "propertyId": property_obj.pk,
                    "isFavorited": True,
                }
            },
        )


class PropertyListViewTests(TestCase):
    def test_applies_discovery_filters(self):
        matching = PropertyFactory(
            name="Lahore family home",
            property_type="House",
            price="18000000",
            bedrooms=3,
        )
        PropertyFactory(
            name="Karachi family home",
            property_type="House",
            price="28000000",
            bedrooms=3,
        )

        response = self.client.get(
            reverse("properties:list"),
            {
                "q": "Lahore",
                "property_type": "House",
                "max_price": "20000000",
                "bedrooms": "3",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context["properties"]), [matching])

    def test_invalid_price_range_is_shown_on_filter_form(self):
        response = self.client.get(
            reverse("properties:list"),
            {"min_price": "20000000", "max_price": "10000000"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response.context["filter_form"],
            "max_price",
            "Maximum price must be at least the minimum.",
        )


class PropertyDownloadDocumentViewTests(TestCase):
    def _pdf_upload(self, name="document.pdf"):
        return SimpleUploadedFile(
            name,
            b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF",
            content_type="application/pdf",
        )

    def test_owner_can_download_document(self):
        owner = UserFactory()
        property_obj = PropertyFactory(user=owner)
        property_obj.documents = self._pdf_upload()
        property_obj.save(update_fields=["documents"])
        self.addCleanup(property_obj.documents.delete, save=False)
        self.client.force_login(owner)

        response = self.client.get(
            reverse("properties:download_document", args=[property_obj.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response["Content-Disposition"], 'attachment; filename="document.pdf"'
        )

    def test_non_owner_receives_forbidden(self):
        owner = UserFactory()
        property_obj = PropertyFactory(user=owner)
        property_obj.documents = self._pdf_upload()
        property_obj.save(update_fields=["documents"])
        self.addCleanup(property_obj.documents.delete, save=False)
        self.client.force_login(UserFactory())

        response = self.client.get(
            reverse("properties:download_document", args=[property_obj.pk])
        )

        self.assertEqual(response.status_code, 403)

    def test_anonymous_user_is_redirected_to_login(self):
        property_obj = PropertyFactory()
        property_obj.documents = self._pdf_upload()
        property_obj.save(update_fields=["documents"])
        self.addCleanup(property_obj.documents.delete, save=False)

        response = self.client.get(
            reverse("properties:download_document", args=[property_obj.pk])
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response["Location"])

    def test_documents_use_private_media_root(self):
        property_obj = PropertyFactory()
        property_obj.documents = self._pdf_upload()
        property_obj.save(update_fields=["documents"])
        self.addCleanup(property_obj.documents.delete, save=False)

        stored_path = Path(property_obj.documents.path)

        self.assertTrue(stored_path.is_file())
        self.assertTrue(stored_path.is_relative_to(settings.PRIVATE_MEDIA_ROOT))
        self.assertFalse(stored_path.is_relative_to(settings.MEDIA_ROOT))
