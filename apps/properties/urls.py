from django.urls import path

from apps.properties.views import (
    FavoritesListView,
    MyPropertiesListView,
    PropertyCreateView,
    PropertyDeleteView,
    PropertyDetailView,
    PropertyDownloadDocumentView,
    PropertyEditView,
    PropertyFavoriteToggleView,
    PropertyListView,
    PropertyPublishToggleView,
)

app_name = "properties"

urlpatterns = [
    path("create/", PropertyCreateView.as_view(), name="create"),
    path("", PropertyListView.as_view(), name="list"),
    path("<int:pk>/", PropertyDetailView.as_view(), name="detail"),
    path("<int:pk>/edit/", PropertyEditView.as_view(), name="edit"),
    path(
        "<int:pk>/download/",
        PropertyDownloadDocumentView.as_view(),
        name="download_document",
    ),
    path(
        "<int:pk>/favorite/",
        PropertyFavoriteToggleView.as_view(),
        name="favorite_toggle",
    ),
    path(
        "<int:pk>/publish/",
        PropertyPublishToggleView.as_view(),
        name="publish_toggle",
    ),
    path("<int:pk>/delete/", PropertyDeleteView.as_view(), name="delete"),
    path("my-properties/", MyPropertiesListView.as_view(), name="my-properties"),
    path("favorites/", FavoritesListView.as_view(), name="favorites"),
]
