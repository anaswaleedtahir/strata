"""
This module contains admin configurations for property-related models.
"""

from django.contrib import admin
from django.utils.safestring import mark_safe

from apps.properties.models import Favorite, Property, PropertyImage


class PropertyImageInline(admin.TabularInline):
    """
    Inline admin class for PropertyImage model.
    """

    model = PropertyImage
    extra = 1
    can_delete = False
    readonly_fields = ("preview_image",)
    fields = ("image", "preview_image", "is_primary")

    def preview_image(self, obj):
        if obj.image:
            return mark_safe(
                f'<img src="{obj.image.url}" style="max-height: 100px;" />'
            )
        return "No image"

    preview_image.short_description = "Preview"  # type: ignore[attr-defined]


class FavoriteInlineForProperty(admin.TabularInline):
    """
    Inline admin to show all users who favorited this property.
    """

    model = Favorite
    extra = 0
    can_delete = False
    readonly_fields = ("user", "created_at")
    fields = ("user", "created_at")
    verbose_name = "User who favorited"
    verbose_name_plural = "Users who favorited this property"
    show_change_link = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    """
    Admin class for Property model.
    """

    list_display = (
        "name",
        "property_type",
        "price",
        "user",
        "created_at",
        "is_published",
    )
    list_filter = ("property_type", "is_published", "created_at")
    search_fields = ("name", "description", "full_address")
    inlines = [PropertyImageInline, FavoriteInlineForProperty]

    def save_model(self, request, obj, form, change):
        if not obj.pk:  # Only set user during the first save.
            obj.user = request.user
        super().save_model(request, obj, form, change)
