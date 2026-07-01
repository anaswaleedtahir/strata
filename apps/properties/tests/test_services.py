from io import BytesIO
import tempfile
from pathlib import Path
from unittest.mock import patch

from django.core.files.storage import FileSystemStorage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from PIL import Image

from apps.properties.models import Property, PropertyImage
from apps.properties.services import (
    IMAGE_MAX_BYTES,
    _delete_storage_file,
    _schedule_storage_deletes,
    favorite_toggle,
    property_create,
    property_delete,
    property_update,
)
from apps.properties.tests.factories import FavoriteFactory, PropertyFactory
from apps.shared.exceptions import ApplicationError
from apps.shared.tests.factories import UserFactory


class RecordingStorage(FileSystemStorage):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.deleted_names: list[str] = []

    def delete(self, name):
        self.deleted_names.append(name)
        return super().delete(name)


class PropertyFileTestMixin:
    def setUp(self):
        super().setUp()
        self.media_root = tempfile.mkdtemp()
        self.private_root = tempfile.mkdtemp()
        self.public_storage = RecordingStorage(location=self.media_root)
        self.private_storage = RecordingStorage(location=self.private_root)
        self._storages_override = override_settings(
            STORAGES={
                "default": {
                    "BACKEND": "django.core.files.storage.FileSystemStorage",
                    "OPTIONS": {"location": self.media_root},
                },
                "private_documents": {
                    "BACKEND": "django.core.files.storage.FileSystemStorage",
                    "OPTIONS": {"location": self.private_root},
                },
                "staticfiles": {
                    "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
                },
            }
        )
        self._storages_override.enable()

    def tearDown(self):
        self._storages_override.disable()
        super().tearDown()

    def _png_upload(self, name="image.png", size=(1, 1)):
        image_bytes = BytesIO()
        Image.new("RGB", size=size, color=(255, 0, 0)).save(image_bytes, format="PNG")
        return SimpleUploadedFile(
            name,
            image_bytes.getvalue(),
            content_type="image/png",
        )

    def _document_upload(self, name="doc.pdf", content=b"%PDF-1.4 test"):
        return SimpleUploadedFile(name, content, content_type="application/pdf")


class StorageHelperTests(TestCase):
    def test_delete_storage_file_ignores_empty_name(self):
        storage = RecordingStorage(location=tempfile.mkdtemp())
        _delete_storage_file(storage=storage, name="")
        self.assertEqual(storage.deleted_names, [])

    def test_schedule_storage_deletes_runs_on_commit(self):
        storage = RecordingStorage(location=tempfile.mkdtemp())
        path = storage.save("scheduled.txt", SimpleUploadedFile("scheduled.txt", b"x"))
        with self.captureOnCommitCallbacks(execute=True):
            _schedule_storage_deletes([(storage, path)])
        self.assertEqual(storage.deleted_names, [path])
        self.assertFalse(storage.exists(path))


class PropertyCreateTests(PropertyFileTestMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.user = UserFactory()
        self.form_data = {
            "name": "Test House",
            "description": "Nice place",
            "full_address": "123 Main St",
            "property_type": "House",
            "price": "5000000.00",
            "bedrooms": 3,
            "bathrooms": 2,
            "area": "1200.00",
            "thumbnail": self._png_upload("thumb.png"),
            "documents": None,
            "is_published": True,
        }

    def test_publishing_without_thumbnail_is_rejected(self):
        form_data = {**self.form_data, "thumbnail": None}
        with self.assertRaisesMessage(
            ApplicationError, "A thumbnail image is required to publish"
        ):
            property_create(user=self.user, form_data=form_data, images=[])
        self.assertEqual(Property.objects.count(), 0)

    def test_draft_without_thumbnail_is_allowed(self):
        form_data = {**self.form_data, "thumbnail": None, "is_published": False}
        prop = property_create(user=self.user, form_data=form_data, images=[])
        self.assertFalse(prop.is_published)
        self.assertFalse(bool(prop.thumbnail))

    def test_thumbnail_is_saved_separately_from_gallery(self):
        prop = property_create(
            user=self.user,
            form_data=self.form_data,
            images=[self._png_upload("gallery.png")],
        )
        self.addCleanup(prop.thumbnail.delete, save=False)
        self.assertTrue(bool(prop.thumbnail))
        self.assertEqual(prop.images.count(), 1)
        self.assertFalse(prop.images.get().is_primary)

    def test_creates_property(self):
        prop = property_create(user=self.user, form_data=self.form_data, images=[])
        self.assertEqual(prop.name, "Test House")
        self.assertEqual(prop.user, self.user)

    def test_property_has_timestamps(self):
        prop = property_create(user=self.user, form_data=self.form_data, images=[])
        self.assertIsNotNone(prop.created_at)
        self.assertIsNotNone(prop.updated_at)

    def test_rollback_removes_new_files_after_partial_image_create(self):
        images = [self._png_upload("one.png"), self._png_upload("two.png")]
        original_save = PropertyImage.save
        save_calls = {"count": 0}

        def failing_save(instance, *args, **kwargs):
            save_calls["count"] += 1
            if save_calls["count"] == 2:
                raise RuntimeError("forced failure")
            return original_save(instance, *args, **kwargs)

        with patch.object(PropertyImage, "save", failing_save):
            with self.assertRaises(RuntimeError):
                property_create(user=self.user, form_data=self.form_data, images=images)

        self.assertEqual(Property.objects.count(), 0)
        self.assertEqual(PropertyImage.objects.count(), 0)
        self.assertEqual(len(list(Path(self.media_root).rglob("*.png"))), 0)

    def test_rollback_removes_new_document_on_failure(self):
        form_data = {
            **self.form_data,
            "documents": self._document_upload(),
        }
        with patch.object(Property, "save", side_effect=RuntimeError("forced failure")):
            with self.assertRaises(RuntimeError):
                property_create(user=self.user, form_data=form_data, images=[])

        self.assertEqual(Property.objects.count(), 0)
        self.assertEqual(len(list(Path(self.private_root).rglob("*"))), 0)

    def test_creates_property_with_valid_image(self):
        prop = property_create(
            user=self.user,
            form_data=self.form_data,
            images=[self._png_upload()],
        )
        image = prop.images.get()
        self.addCleanup(image.image.delete, save=False)

        self.assertEqual(Property.objects.count(), 1)
        self.assertEqual(PropertyImage.objects.count(), 1)
        self.assertGreater(image.image.size, 0)

    def test_rejects_invalid_image_content(self):
        with self.assertRaisesMessage(ApplicationError, "Upload a valid image file."):
            property_create(
                user=self.user,
                form_data=self.form_data,
                images=[
                    SimpleUploadedFile(
                        "fake.png",
                        b"not an image",
                        content_type="image/png",
                    )
                ],
            )

        self.assertEqual(Property.objects.count(), 0)
        self.assertEqual(PropertyImage.objects.count(), 0)

    def test_rejects_oversize_image(self):
        with self.assertRaisesMessage(
            ApplicationError, "Image 'huge.png' exceeds the 5MB limit."
        ):
            property_create(
                user=self.user,
                form_data=self.form_data,
                images=[
                    SimpleUploadedFile(
                        "huge.png",
                        b"x" * (IMAGE_MAX_BYTES + 1),
                        content_type="image/png",
                    )
                ],
            )

        self.assertEqual(Property.objects.count(), 0)
        self.assertEqual(PropertyImage.objects.count(), 0)


class PropertyUpdateStorageTests(PropertyFileTestMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.user = UserFactory()
        self.prop = property_create(
            user=self.user,
            form_data={
                "name": "Existing",
                "description": "",
                "full_address": "1 Old St",
                "property_type": "House",
                "price": "1000000.00",
                "thumbnail": self._png_upload("old-thumb.png"),
                "documents": self._document_upload("old.pdf"),
                "is_published": True,
            },
            images=[self._png_upload("old.png")],
        )
        self.prop.refresh_from_db()
        self.original_doc_name = self.prop.documents.name
        self.original_image = self.prop.images.get()
        self.original_image_name = self.original_image.image.name

    def test_rollback_preserves_original_files_and_removes_new_uploads(self):
        with patch.object(
            PropertyImage,
            "save",
            side_effect=RuntimeError("forced failure"),
        ):
            with self.assertRaises(RuntimeError):
                property_update(
                    property_obj=self.prop,
                    form_data={"documents": self._document_upload("new.pdf")},
                    images=[self._png_upload("new.png")],
                    delete_image_ids=[],
                    remove_document=False,
                )

        self.prop.refresh_from_db()
        self.assertEqual(self.prop.documents.name, self.original_doc_name)
        self.assertTrue(self.prop.documents.storage.exists(self.original_doc_name))
        self.assertEqual(self.prop.images.count(), 1)
        self.assertTrue(
            self.original_image.image.storage.exists(self.original_image_name)
        )
        self.assertEqual(len(list(Path(self.media_root).rglob("new.png"))), 0)
        self.assertEqual(len(list(Path(self.private_root).rglob("new.pdf"))), 0)

    def test_document_replacement_deletes_old_file_after_commit(self):
        new_doc = self._document_upload("replacement.pdf")
        with self.captureOnCommitCallbacks(execute=False) as callbacks:
            property_update(
                property_obj=self.prop,
                form_data={"documents": new_doc},
                images=[],
                delete_image_ids=[],
                remove_document=False,
            )

        self.prop.refresh_from_db()
        self.assertTrue(self.prop.documents.storage.exists(self.original_doc_name))
        self.assertTrue(self.prop.documents.storage.exists(self.prop.documents.name))

        for callback in callbacks:
            callback()
        self.assertFalse(self.prop.documents.storage.exists(self.original_doc_name))
        self.assertTrue(self.prop.documents.storage.exists(self.prop.documents.name))

    def test_image_removal_deletes_file_after_commit(self):
        image_id = self.original_image.pk
        image_name = self.original_image_name
        storage = self.original_image.image.storage

        with self.captureOnCommitCallbacks(execute=False) as callbacks:
            property_update(
                property_obj=self.prop,
                form_data={},
                images=[],
                delete_image_ids=[image_id],
                remove_document=False,
            )

        self.assertFalse(PropertyImage.objects.filter(pk=image_id).exists())
        self.assertTrue(storage.exists(image_name))

        for callback in callbacks:
            callback()
        self.assertFalse(storage.exists(image_name))


class PropertyDeleteTests(PropertyFileTestMixin, TestCase):
    def test_deletes_property(self):
        prop = PropertyFactory()
        pk = prop.pk
        property_delete(property_obj=prop)

        self.assertFalse(Property.objects.filter(pk=pk).exists())

    def test_deletes_files_after_database_commit(self):
        prop = property_create(
            user=UserFactory(),
            form_data={
                "name": "Delete Me",
                "description": "",
                "full_address": "9 Delete Ave",
                "property_type": "House",
                "price": "250000.00",
                "thumbnail": self._png_upload("delete-thumb.png"),
                "documents": self._document_upload(),
                "is_published": True,
            },
            images=[self._png_upload()],
        )
        image = prop.images.get()
        doc_name = prop.documents.name
        image_name = image.image.name
        doc_storage = prop.documents.storage
        image_storage = image.image.storage
        pk = prop.pk

        with self.captureOnCommitCallbacks(execute=False) as callbacks:
            property_delete(property_obj=prop)

        self.assertFalse(Property.objects.filter(pk=pk).exists())
        self.assertTrue(doc_storage.exists(doc_name))
        self.assertTrue(image_storage.exists(image_name))

        for callback in callbacks:
            callback()
        self.assertFalse(doc_storage.exists(doc_name))
        self.assertFalse(image_storage.exists(image_name))

    def test_storage_delete_failure_does_not_restore_database_row(self):
        prop = property_create(
            user=UserFactory(),
            form_data={
                "name": "Orphan Risk",
                "description": "",
                "full_address": "10 Risk Rd",
                "property_type": "House",
                "price": "250000.00",
                "thumbnail": self._png_upload("orphan-thumb.png"),
                "documents": None,
                "is_published": True,
            },
            images=[self._png_upload()],
        )
        image = prop.images.get()
        pk = prop.pk
        storage = image.image.storage
        name = image.image.name

        with patch.object(
            storage,
            "delete",
            side_effect=OSError("storage unavailable"),
        ):
            with self.captureOnCommitCallbacks(execute=True):
                property_delete(property_obj=prop)

        self.assertFalse(Property.objects.filter(pk=pk).exists())
        self.assertTrue(storage.exists(name))


class FavoriteToggleTests(TestCase):
    def test_adds_favorite(self):
        user = UserFactory()
        prop = PropertyFactory()
        result = favorite_toggle(user=user, property_obj=prop)
        self.assertTrue(result)

    def test_removes_favorite(self):
        fav = FavoriteFactory()
        result = favorite_toggle(user=fav.user, property_obj=fav.property)
        self.assertFalse(result)

    def test_toggle_twice_removes_then_adds(self):
        user = UserFactory()
        prop = PropertyFactory()
        favorite_toggle(user=user, property_obj=prop)
        favorite_toggle(user=user, property_obj=prop)
        result = favorite_toggle(user=user, property_obj=prop)
        self.assertTrue(result)
