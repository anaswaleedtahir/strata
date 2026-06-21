from django import forms
from django.core.exceptions import ValidationError
from django.db import transaction

from apps.properties.models import Favorite, Property, PropertyImage
from apps.shared.exceptions import ApplicationError

DOCUMENT_MAX_BYTES = 10 * 1024 * 1024
IMAGE_MAX_BYTES = 5 * 1024 * 1024


def _validate_document_size(document) -> None:
    if document and getattr(document, "size", 0) > DOCUMENT_MAX_BYTES:
        raise ApplicationError("Document file size must not exceed 10MB.")


def _validate_images(images) -> list:
    cleaned_images = []
    image_field = forms.ImageField()
    for image in images or []:
        if getattr(image, "size", 0) > IMAGE_MAX_BYTES:
            raise ApplicationError(
                f"Image '{getattr(image, 'name', 'unknown')}' exceeds the 5MB limit."
            )
        try:
            cleaned_image = image_field.clean(image)
        except ValidationError as exc:
            raise ApplicationError("Upload a valid image file.") from exc
        if hasattr(cleaned_image, "seek"):
            cleaned_image.seek(0)
        cleaned_images.append(cleaned_image)
    return cleaned_images


def _storage_ref(field_file) -> tuple | None:
    if not field_file or not field_file.name:
        return None
    return (field_file.storage, field_file.name)


def _delete_storage_file(*, storage, name: str) -> None:
    if not name:
        return
    try:
        storage.delete(name)
    except Exception:
        pass


def _schedule_storage_deletes(refs: list[tuple]) -> None:
    for storage, name in refs:
        if name:
            transaction.on_commit(
                lambda s=storage, n=name: _delete_storage_file(storage=s, name=n)
            )


class _NewFileTracker:
    def __init__(self) -> None:
        self._refs: set[tuple[int, str, object]] = set()

    def track(self, field_file) -> None:
        ref = _storage_ref(field_file)
        if ref is not None:
            storage, name = ref
            self._refs.add((id(storage), name, storage))

    def cleanup(self) -> None:
        for _, name, storage in self._refs:
            _delete_storage_file(storage=storage, name=name)
        self._refs.clear()


def property_image_add(
    *,
    property_obj: Property,
    image_file,
    is_primary: bool,
    new_files: _NewFileTracker | None = None,
) -> PropertyImage:
    with transaction.atomic():
        if is_primary:
            property_obj.images.filter(is_primary=True).update(is_primary=False)
        image = PropertyImage(
            property=property_obj, image=image_file, is_primary=is_primary
        )
        image.full_clean()
        try:
            image.save()
        except Exception:
            ref = _storage_ref(image.image)
            if ref is not None and new_files is None:
                storage, name = ref
                _delete_storage_file(storage=storage, name=name)
            raise
        if new_files is not None:
            new_files.track(image.image)
    return image


def property_create(*, user, form_data: dict, images: list) -> Property:
    _validate_document_size(form_data.get("documents"))
    cleaned_images = _validate_images(images)

    prop = Property(
        user=user,
        name=form_data["name"],
        description=form_data.get("description", ""),
        full_address=form_data["full_address"],
        property_type=form_data["property_type"],
        price=form_data["price"],
        bedrooms=form_data.get("bedrooms"),
        bathrooms=form_data.get("bathrooms"),
        area=form_data.get("area"),
        documents=form_data.get("documents") or None,
        is_published=form_data.get("is_published", False),
    )
    prop.full_clean()
    new_files = _NewFileTracker()
    try:
        with transaction.atomic():
            prop.save()
            if prop.documents:
                new_files.track(prop.documents)
            for idx, image_file in enumerate(cleaned_images):
                property_image_add(
                    property_obj=prop,
                    image_file=image_file,
                    is_primary=(idx == 0),
                    new_files=new_files,
                )
    except Exception:
        new_files.cleanup()
        raise

    return prop


def property_update(
    *,
    property_obj: Property,
    form_data: dict,
    images: list,
    delete_image_ids: list,
    remove_document: bool,
) -> Property:
    _validate_document_size(form_data.get("documents"))
    cleaned_images = _validate_images(images)

    non_file_fields = [
        "name",
        "description",
        "full_address",
        "property_type",
        "price",
        "bedrooms",
        "bathrooms",
        "area",
        "is_published",
    ]
    for field in non_file_fields:
        if field in form_data:
            setattr(property_obj, field, form_data[field])

    old_document_ref = None
    new_doc = form_data.get("documents")
    if new_doc and new_doc is not False:
        if property_obj.documents:
            old_document_ref = _storage_ref(property_obj.documents)
        property_obj.documents = new_doc

    images_to_delete: list[tuple] = []
    if delete_image_ids:
        for img in PropertyImage.objects.filter(
            id__in=delete_image_ids, property=property_obj
        ):
            ref = _storage_ref(img.image)
            if ref is not None:
                images_to_delete.append(ref)

    property_obj.full_clean()
    new_files = _NewFileTracker()
    try:
        with transaction.atomic():
            property_obj.save()
            if new_doc and new_doc is not False and property_obj.documents:
                new_files.track(property_obj.documents)

            pending_deletes: list[tuple] = []
            if remove_document and property_obj.documents:
                ref = _storage_ref(property_obj.documents)
                if ref is not None:
                    pending_deletes.append(ref)
                property_obj.documents = None
                property_obj.save(update_fields=["documents"])

            if delete_image_ids:
                PropertyImage.objects.filter(
                    id__in=delete_image_ids, property=property_obj
                ).delete()

            if cleaned_images:
                existing_count = property_obj.images.count()
                for idx, image_file in enumerate(cleaned_images):
                    property_image_add(
                        property_obj=property_obj,
                        image_file=image_file,
                        is_primary=(idx == 0 and existing_count == 0),
                        new_files=new_files,
                    )

            if old_document_ref is not None:
                pending_deletes.append(old_document_ref)
            pending_deletes.extend(images_to_delete)
            _schedule_storage_deletes(pending_deletes)
    except Exception:
        new_files.cleanup()
        raise

    return property_obj


def property_delete(*, property_obj: Property) -> None:
    pending_deletes: list[tuple] = []
    for img in property_obj.images.all():
        ref = _storage_ref(img.image)
        if ref is not None:
            pending_deletes.append(ref)
    doc_ref = _storage_ref(property_obj.documents)
    if doc_ref is not None:
        pending_deletes.append(doc_ref)

    with transaction.atomic():
        property_obj.delete()
        _schedule_storage_deletes(pending_deletes)


def favorite_toggle(*, user, property_obj: Property) -> bool:
    favorite, created = Favorite.objects.get_or_create(user=user, property=property_obj)
    if not created:
        favorite.delete()
        return False
    return True
