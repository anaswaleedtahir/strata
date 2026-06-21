"""
This module contains URL patterns for user-related operations.
"""

from django.urls import path

from apps.users.views import (
    ProfileEditView,
    ProfileView,
)

app_name = "users"

urlpatterns = [
    path("profile/", ProfileView.as_view(), name="profile"),
    path("profile/edit/", ProfileEditView.as_view(), name="profile_edit"),
]
