"""
This module contains admin configurations for user-related models.
"""

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from apps.properties.models import Favorite

User = get_user_model()


class FavoriteInlineForUser(admin.TabularInline):
    """
    Inline admin to show all properties favorited by this user.
    """

    model = Favorite
    extra = 0
    readonly_fields = ("property", "created_at")
    verbose_name = "Favorited property"
    verbose_name_plural = "Properties favorited by this user"


class UserAdmin(BaseUserAdmin):
    """
    Custom User admin that uses email as the primary identifier.
    Only superusers can access the admin panel.
    """

    inlines = [FavoriteInlineForUser]

    # Fields to display in the user list
    list_display = ("email", "first_name", "last_name", "is_superuser", "is_active")
    list_filter = ("is_superuser", "is_active")

    # Fields for the user detail/edit page
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal info", {"fields": ("first_name", "last_name")}),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )

    # Fields for the add user page
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "first_name",
                    "last_name",
                    "password1",
                    "password2",
                    "is_superuser",
                    "is_active",
                ),
            },
        ),
    )

    search_fields = ("email", "first_name", "last_name")
    ordering = ("email",)


# Register our custom User admin
admin.site.register(User, UserAdmin)
