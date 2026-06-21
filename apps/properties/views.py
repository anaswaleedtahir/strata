"""HTTP views for Property discovery and management."""

import logging
import os

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.http import (
    FileResponse,
    Http404,
    HttpResponseForbidden,
    JsonResponse,
)
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View
from django_htmx.http import HttpResponseClientRedirect, trigger_client_event

from apps.properties.forms import PropertyFilterForm, PropertyForm
from apps.properties.models import Property
from apps.properties.selectors import (
    favorite_exists,
    favorite_ids_for_user,
    property_get_with_related,
    property_counts_for_user,
    property_list_favorites_for_user,
    property_list_for_user,
    property_list_published,
)
from apps.properties.services import (
    favorite_toggle,
    property_create,
    property_delete,
    property_update,
)
from apps.shared.exceptions import ApplicationError
from apps.shared.mixins import HTMXMixin, OwnerRequiredMixin

logger = logging.getLogger(__name__)


class PropertyListView(HTMXMixin, View):
    def get(self, request):
        show_favorites = request.GET.get("favorites") == "true"
        show_my_properties = request.GET.get("my_properties") == "true"

        user = request.user if request.user.is_authenticated else None
        filter_form = PropertyFilterForm(request.GET)
        filters = {}
        if filter_form.is_valid():
            cleaned_data = filter_form.cleaned_data
            filters = {
                "query": cleaned_data.get("q", ""),
                "property_type": cleaned_data.get("property_type", ""),
                "min_price": cleaned_data.get("min_price"),
                "max_price": cleaned_data.get("max_price"),
                "bedrooms": cleaned_data.get("bedrooms"),
                "bathrooms": cleaned_data.get("bathrooms"),
                "ordering": cleaned_data.get("sort") or "newest",
            }

        properties = property_list_published(
            user=user,
            show_favorites=show_favorites,
            show_my_properties=show_my_properties,
            **filters,
        )

        if not request.user.is_authenticated:
            show_favorites = False
            show_my_properties = False

        page_number = request.GET.get("page", 1)
        paginator = Paginator(properties, 10)
        page_obj = paginator.get_page(page_number)

        favorited_ids = set()
        if request.user.is_authenticated:
            favorited_ids = favorite_ids_for_user(user=request.user)

        for prop in page_obj.object_list:
            prop.is_favorited = prop.id in favorited_ids

        context = {
            "page_obj": page_obj,
            "properties": page_obj.object_list,
            "show_favorites": show_favorites,
            "show_my_properties": show_my_properties,
            "filter_form": filter_form,
        }

        if self.is_htmx:
            return render(request, "properties/partials/property_results.html", context)
        return render(request, "properties/list.html", context)


class PropertyDetailView(HTMXMixin, View):
    def get(self, request, pk):
        property_obj = property_get_with_related(pk=pk)
        if property_obj is None:
            raise Http404("Property not found")

        is_owner = request.user.is_authenticated and property_obj.user == request.user
        if not property_obj.is_published and not is_owner:
            raise Http404("Property not found")

        is_favorited = False
        if request.user.is_authenticated:
            is_favorited = favorite_exists(user=request.user, property_obj=property_obj)
        property_obj.is_favorited = is_favorited

        context = {
            "property": property_obj,
            "is_favorited": is_favorited,
            "is_owner": is_owner,
        }

        if self.is_htmx:
            return render(request, "properties/partials/property_detail.html", context)
        return render(request, "properties/detail.html", context)


class PropertyCreateView(LoginRequiredMixin, HTMXMixin, View):
    def get(self, request):
        form = PropertyForm()
        template = (
            "properties/partials/property_form.html"
            if self.is_htmx
            else "properties/create.html"
        )
        return render(request, template, {"form": form, "is_edit_mode": False})

    def post(self, request):
        form = PropertyForm(request.POST, request.FILES)
        images = request.FILES.getlist("images")

        if form.is_valid():
            try:
                form_data = {
                    **form.cleaned_data,
                    "is_published": request.POST.get("intent") == "publish",
                }
                property_obj = property_create(
                    user=request.user, form_data=form_data, images=images
                )
            except ApplicationError as e:
                form.add_error(None, e.message)
            except Exception as e:
                logger.error(f"Error creating property: {e}", exc_info=True)
                form.add_error(
                    None,
                    "An error occurred while creating the property. Please try again.",
                )
            else:
                messages.success(
                    request, f'Property "{property_obj.name}" created successfully!'
                )
                if self.is_htmx:
                    return HttpResponseClientRedirect(
                        reverse("properties:detail", args=[property_obj.pk])
                    )
                return redirect("properties:detail", pk=property_obj.pk)

        template = (
            "properties/partials/property_form.html"
            if self.is_htmx
            else "properties/create.html"
        )
        return render(request, template, {"form": form, "is_edit_mode": False})


class PropertyEditView(LoginRequiredMixin, OwnerRequiredMixin, HTMXMixin, View):
    def _get_property(self, pk):
        property_obj = get_object_or_404(Property, pk=pk)
        self.check_owner(property_obj)
        return property_obj

    def get(self, request, pk):
        property_obj = self._get_property(pk)
        form = PropertyForm(instance=property_obj)
        template = (
            "properties/partials/property_form.html"
            if self.is_htmx
            else "properties/edit.html"
        )
        return render(
            request,
            template,
            {"form": form, "property": property_obj, "is_edit_mode": True},
        )

    def post(self, request, pk):
        property_obj = self._get_property(pk)
        form = PropertyForm(request.POST, request.FILES, instance=property_obj)
        new_images = request.FILES.getlist("images")
        delete_image_ids = request.POST.getlist("delete_image_ids")
        remove_document = request.POST.get("remove_document") == "true"

        if form.is_valid():
            try:
                form_data = {
                    **form.cleaned_data,
                    "is_published": request.POST.get("intent") == "publish",
                }
                property_obj = property_update(
                    property_obj=property_obj,
                    form_data=form_data,
                    images=new_images,
                    delete_image_ids=delete_image_ids,
                    remove_document=remove_document,
                )
            except ApplicationError as e:
                form.add_error(None, e.message)
            except Exception as e:
                logger.error(
                    f"Error updating property {property_obj.pk}: {e}", exc_info=True
                )
                form.add_error(
                    None,
                    "An error occurred while updating the property. Please try again.",
                )
            else:
                messages.success(
                    request, f'Property "{property_obj.name}" updated successfully!'
                )
                if self.is_htmx:
                    return HttpResponseClientRedirect(
                        reverse("properties:detail", args=[property_obj.pk])
                    )
                return redirect("properties:detail", pk=property_obj.pk)

        template = (
            "properties/partials/property_form.html"
            if self.is_htmx
            else "properties/edit.html"
        )
        return render(
            request,
            template,
            {"form": form, "property": property_obj, "is_edit_mode": True},
        )


class MyPropertiesListView(LoginRequiredMixin, View):
    def get(self, request):
        properties = property_list_for_user(user=request.user)
        page_obj = Paginator(properties, 10).get_page(request.GET.get("page", 1))

        context = {
            "properties": page_obj.object_list,
            "page_obj": page_obj,
            "property_counts": property_counts_for_user(user=request.user),
        }
        return render(request, "properties/my-properties.html", context)


class FavoritesListView(LoginRequiredMixin, View):
    def get(self, request):
        favorite_properties = property_list_favorites_for_user(user=request.user)
        page_obj = Paginator(favorite_properties, 10).get_page(
            request.GET.get("page", 1)
        )

        for prop in page_obj.object_list:
            prop.is_favorited = True

        context = {"properties": page_obj.object_list, "page_obj": page_obj}
        return render(request, "properties/favorites.html", context)


class PropertyDownloadDocumentView(LoginRequiredMixin, View):
    def get(self, request, pk):
        property_obj = get_object_or_404(Property, pk=pk)

        if property_obj.user != request.user and not request.user.is_superuser:
            return HttpResponseForbidden(
                "You are not authorized to download this document."
            )
        if not property_obj.documents:
            return HttpResponseForbidden("No document available.")

        return FileResponse(
            property_obj.documents,
            as_attachment=True,
            filename=os.path.basename(str(property_obj.documents.name)),
        )


class PropertyFavoriteToggleView(LoginRequiredMixin, View):
    def post(self, request, pk):
        property_obj = get_object_or_404(Property, pk=pk)

        is_owner = property_obj.user == request.user
        if not property_obj.is_published and not is_owner:
            raise Http404("Property not found")

        is_favorited = favorite_toggle(user=request.user, property_obj=property_obj)

        if request.htmx:
            property_obj.is_favorited = is_favorited
            response = render(
                request,
                "cotton/properties/favorite_button.html",
                {"property": property_obj},
            )
            return trigger_client_event(
                response,
                "favorite-toggled",
                {"propertyId": property_obj.pk, "isFavorited": is_favorited},
            )

        return JsonResponse({"is_favorited": is_favorited})


class PropertyDeleteView(LoginRequiredMixin, OwnerRequiredMixin, HTMXMixin, View):
    def post(self, request, pk):
        property_obj = get_object_or_404(Property, pk=pk)
        self.check_owner(property_obj)

        property_delete(property_obj=property_obj)
        messages.success(request, "Property deleted successfully.")

        if self.is_htmx:
            return HttpResponseClientRedirect(reverse("properties:list"))
        return redirect("properties:list")
