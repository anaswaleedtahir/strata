from django.db import transaction

from apps.properties.models import Favorite, Property, PropertyImage
from apps.shared.exceptions import ApplicationError

DOCUMENT_MAX_BYTES = 10 * 1024 * 1024
IMAGE_MAX_BYTES = 5 * 1024 * 1024


def _validate_document_size(document) -> None:
    if document and getattr(document, "size", 0) > DOCUMENT_MAX_BYTES:
        raise ApplicationError("Document file size must not exceed 10MB.")


def _validate_image_sizes(images) -> None:
    for image in images or []:
        if getattr(image, "size", 0) > IMAGE_MAX_BYTES:
            raise ApplicationError(
                f"Image '{getattr(image, 'name', 'unknown')}' exceeds the 5MB limit."
            )


def property_image_add(
    *, property_obj: Property, image_file, is_primary: bool
) -> PropertyImage:
    with transaction.atomic():
        if is_primary:
            property_obj.images.filter(is_primary=True).update(is_primary=False)
        image = PropertyImage(
            property=property_obj, image=image_file, is_primary=is_primary
        )
        image.save()
    return image


def property_create(*, user, form_data: dict, images: list) -> Property:
    _validate_document_size(form_data.get("documents"))
    _validate_image_sizes(images)

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
    with transaction.atomic():
        prop.save()
        for idx, image_file in enumerate(images or []):
            property_image_add(
                property_obj=prop, image_file=image_file, is_primary=(idx == 0)
            )

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
    _validate_image_sizes(images)

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

    new_doc = form_data.get("documents")
    if new_doc and new_doc is not False:
        property_obj.documents = new_doc

    property_obj.full_clean()
    with transaction.atomic():
        property_obj.save()

        if remove_document and property_obj.documents:
            property_obj.documents.delete(save=False)
            property_obj.documents = None
            property_obj.save(update_fields=["documents"])

        if delete_image_ids:
            PropertyImage.objects.filter(
                id__in=delete_image_ids, property=property_obj
            ).delete()

        if images:
            existing_count = property_obj.images.count()
            for idx, image_file in enumerate(images):
                property_image_add(
                    property_obj=property_obj,
                    image_file=image_file,
                    is_primary=(idx == 0 and existing_count == 0),
                )

    return property_obj


def property_delete(*, property_obj: Property) -> None:
    for img in property_obj.images.all():
        img.image.delete(save=False)
    if property_obj.documents:
        property_obj.documents.delete(save=False)
    property_obj.delete()


def favorite_toggle(*, user, property_obj: Property) -> bool:
    favorite, created = Favorite.objects.get_or_create(user=user, property=property_obj)
    if not created:
        favorite.delete()
        return False
    return True
