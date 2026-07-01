"""Models for property-related operations.

Improvements for modern Django and Python:
- Use settings.AUTH_USER_MODEL instead of direct User import.
- Safer upload paths that handle unsaved instances.
- Published manager helper and small convenience methods.
- DB indexes for common lookups.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.conf import settings
from django.core.files.storage import storages
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Index, UniqueConstraint
from django.urls import reverse

from apps.shared.models import BaseModel

# Historical migrations import these names from this module.
from apps.shared.validators import cnic_validator, phone_validator  # noqa: F401

if TYPE_CHECKING:
    from django.db.models.manager import RelatedManager


def documents_upload_path(instance: "Property", filename: str) -> str:
    """Generate upload path for property documents.

    Use instance.id when available; fall back to 'temp' so file uploads won't error for unsaved instances.
    """
    pid = getattr(instance, "id", None) or "temp"
    return f"properties/documents/{pid}/{filename}"


def property_image_upload_path(instance: "PropertyImage", filename: str) -> str:
    """Generate upload path for property images.

    Safe to call before the related Property is saved by using property_id.
    """
    prop_id = (
        getattr(instance, "property_id", None)
        or getattr(instance.property, "id", None)
        or "temp"
    )
    return f"properties/images/{prop_id}/{filename}"


def property_thumbnail_upload_path(instance: "Property", filename: str) -> str:
    """Generate upload path for a property's thumbnail image.

    Use instance.id when available; fall back to 'temp' for unsaved instances.
    """
    pid = getattr(instance, "id", None) or "temp"
    return f"properties/thumbnails/{pid}/{filename}"


def private_document_storage():
    return storages["private_documents"]


class Property(BaseModel):
    """Model representing a property."""

    PROPERTY_TYPE = (
        ("House", "House"),
        ("Plot", "Plot"),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="properties"
    )
    name = models.CharField(max_length=255)
    full_address = models.CharField(max_length=255)
    thumbnail = models.ImageField(
        upload_to=property_thumbnail_upload_path,
        blank=True,
        null=True,
        help_text="Primary image shown on cards, the map, and as the lead photo. Required to publish.",
    )
    property_type = models.CharField(max_length=10, choices=PROPERTY_TYPE)
    description = models.TextField(blank=True)
    # Use 2 decimal places for currency precision. Note: changing this requires a migration.
    price = models.DecimalField(
        max_digits=12, decimal_places=2, validators=[MinValueValidator(0)]
    )
    bedrooms = models.PositiveIntegerField(
        blank=True, null=True, help_text="Number of bedrooms"
    )
    bathrooms = models.PositiveIntegerField(
        blank=True, null=True, help_text="Number of bathrooms"
    )
    area = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(0)],
        help_text="Property area in square feet",
    )
    documents = models.FileField(
        upload_to=documents_upload_path,
        storage=private_document_storage,
        blank=True,
        null=True,
    )
    is_published = models.BooleanField(default=False, db_index=True)

    if TYPE_CHECKING:
        images: RelatedManager[PropertyImage]
        favorited_by: RelatedManager[Favorite]

    class Meta:
        verbose_name_plural = "Properties"
        ordering = ["-created_at"]
        indexes = [Index(fields=["price"])]

    def __str__(self) -> str:  # pragma: no cover - simple representation
        return str(self.name)

    def __repr__(self) -> str:
        return f"<Property id={self.pk!r} name={self.name!r}>"

    def get_absolute_url(self) -> str:
        return reverse("properties:detail", args=[self.pk])


class PropertyImage(BaseModel):
    """Model representing a gallery image of a property.

    The representative image shown on cards, the map, and as the lead photo is
    Property.thumbnail; these are additional gallery photos.
    """

    property = models.ForeignKey(
        Property, on_delete=models.CASCADE, related_name="images"
    )
    image = models.ImageField(upload_to=property_image_upload_path)

    class Meta:
        ordering = ["created_at"]
        verbose_name = "Property Image"
        verbose_name_plural = "Property Images"

    def __str__(self) -> str:
        return f"Image for {self.property.name}"


class Favorite(BaseModel):
    """Model representing a favorite property."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="user_favorites",
    )
    property = models.ForeignKey(
        Property, on_delete=models.CASCADE, related_name="favorited_by"
    )

    class Meta:
        constraints = [
            UniqueConstraint(
                fields=["user", "property"], name="unique_user_property_favorite"
            )
        ]
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{getattr(self.user, 'username', str(self.user))} favorited {self.property.name}"
