"""Models for property-related operations.

Improvements for modern Django and Python:
- Use settings.AUTH_USER_MODEL instead of direct User import.
- Add validators for phone and CNIC fields.
- Safer upload paths that handle unsaved instances.
- Published manager helper and small convenience methods.
- DB indexes and conditional UniqueConstraint for primary images.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Index, Q, UniqueConstraint
from django.urls import reverse

from apps.shared.models import BaseModel
from apps.shared.validators import cnic_validator, phone_validator

if TYPE_CHECKING:
    from django.db.models.manager import RelatedManager


class PublishedManager(models.Manager):
    """Manager that returns only published properties."""

    def get_queryset(self):
        return super().get_queryset().filter(is_published=True)


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
    phone_number = models.CharField(max_length=16, validators=[phone_validator])
    cnic = models.CharField(max_length=15, validators=[cnic_validator])
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
    documents = models.FileField(upload_to=documents_upload_path, blank=True, null=True)
    is_published = models.BooleanField(default=False, db_index=True)

    # Managers
    objects = models.Manager()
    published = PublishedManager()

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
        """Return canonical URL for a property detail page.

        Note: adjust the URL name if your app uses a different one.
        """
        try:
            return reverse("properties:detail", args=[self.pk])
        except Exception:
            # Fallback to a simple path if reverse isn't configured
            return f"/properties/{self.pk}/"

    def primary_image(self) -> Optional["PropertyImage"]:
        """Return the primary image for this property, or the first image if none marked primary."""
        return self.images.filter(is_primary=True).first() or self.images.first()


class PropertyImage(BaseModel):
    """Model representing an image of a property."""

    property = models.ForeignKey(
        Property, on_delete=models.CASCADE, related_name="images"
    )
    image = models.ImageField(upload_to=property_image_upload_path)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    is_primary = models.BooleanField(default=False, help_text="Mark as primary image")

    class Meta:
        ordering = ["-is_primary", "uploaded_at"]
        verbose_name = "Property Image"
        verbose_name_plural = "Property Images"
        constraints = [
            # Ensure only one primary image per property at the DB level
            UniqueConstraint(
                fields=["property"],
                condition=Q(is_primary=True),
                name="one_primary_image_per_property",
            )
        ]

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
    favorited_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            UniqueConstraint(
                fields=["user", "property"], name="unique_user_property_favorite"
            )
        ]
        ordering = ["-favorited_at"]

    def __str__(self) -> str:
        return f"{getattr(self.user, 'username', str(self.user))} favorited {self.property.name}"
