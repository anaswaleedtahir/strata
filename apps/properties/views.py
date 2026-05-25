import json
import logging
import os

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.http import (
    FileResponse,
    Http404,
    HttpResponse,
    HttpResponseForbidden,
    JsonResponse,
)
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View

from apps.properties.forms import PropertyForm
from apps.properties.models import Property
from apps.properties.selectors import (
    favorite_exists,
    favorite_ids_for_user,
    property_get_with_related,
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
from apps.shared.validators import cnic_validator, phone_validator

logger = logging.getLogger(__name__)


class PropertyListView(HTMXMixin, View):
    def get(self, request):
        show_favorites = request.GET.get("favorites") == "true"
        show_my_properties = request.GET.get("my_properties") == "true"

        user = request.user if request.user.is_authenticated else None
        properties = property_list_published(
            user=user,
            show_favorites=show_favorites,
            show_my_properties=show_my_properties,
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
        }

        if self.is_htmx:
            return render(request, "_components/properties/property_grid.html", context)
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
            return render(
                request, "_components/properties/property_detail.html", context
            )
        return render(request, "properties/detail.html", context)


class PropertyCreateView(LoginRequiredMixin, HTMXMixin, View):
    def get(self, request):
        form = PropertyForm()
        template = (
            "_components/properties/property_form.html"
            if self.is_htmx
            else "properties/create.html"
        )
        return render(request, template, {"form": form, "is_edit_mode": False})

    def post(self, request):
        form = PropertyForm(request.POST, request.FILES)
        images = request.FILES.getlist("images")

        if form.is_valid():
            try:
                property_obj = property_create(
                    user=request.user, form_data=form.cleaned_data, images=images
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
                    response = HttpResponse()
                    response["HX-Redirect"] = reverse(
                        "properties:detail", args=[property_obj.pk]
                    )
                    return response
                return redirect("properties:detail", pk=property_obj.pk)

        template = (
            "_components/properties/property_form.html"
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
            "_components/properties/property_form.html"
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
                property_obj = property_update(
                    property_obj=property_obj,
                    form_data=form.cleaned_data,
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
                    response = HttpResponse()
                    response["HX-Redirect"] = reverse(
                        "properties:detail", args=[property_obj.pk]
                    )
                    return response
                return redirect("properties:detail", pk=property_obj.pk)

        template = (
            "_components/properties/property_form.html"
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

        context = {"properties": page_obj.object_list, "page_obj": page_obj}
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

        if request.headers.get("HX-Request"):
            property_obj.is_favorited = is_favorited
            response = render(
                request,
                "_components/properties/favorite_button.html",
                {"property": property_obj},
            )
            response["HX-Trigger"] = json.dumps(
                {
                    "favorite-toggled": {
                        "propertyId": property_obj.pk,
                        "isFavorited": is_favorited,
                    }
                }
            )
            return response

        return JsonResponse({"is_favorited": is_favorited})


class PropertyDeleteView(LoginRequiredMixin, OwnerRequiredMixin, HTMXMixin, View):
    def post(self, request, pk):
        property_obj = get_object_or_404(Property, pk=pk)
        self.check_owner(property_obj)

        property_delete(property_obj=property_obj)
        messages.success(request, "Property deleted successfully.")

        if self.is_htmx:
            response = HttpResponse()
            response["HX-Redirect"] = reverse("properties:list")
            return response
        return redirect("properties:list")


class PropertyValidateStepView(LoginRequiredMixin, View):
    STEP_FIELDS = {
        "1": ["name", "property_type", "price", "full_address"],
        "2": ["bedrooms", "bathrooms", "area", "phone_number", "cnic"],
        "3": [],
        "4": [],
    }

    def post(self, request):
        step = request.POST.get("step")
        if not step or step not in self.STEP_FIELDS:
            return JsonResponse({"error": "Invalid step parameter"}, status=400)

        fields_to_validate = self.STEP_FIELDS[step]
        if not fields_to_validate:
            return JsonResponse({"valid": True})

        form = PropertyForm(request.POST, request.FILES)
        form.is_valid()
        errors = {
            field: form.errors[field]
            for field in fields_to_validate
            if field in form.errors
        }

        if errors:
            return JsonResponse({"valid": False, "errors": errors})
        return JsonResponse({"valid": True})


class ValidatePhoneView(View):
    def post(self, request):
        phone_number = request.POST.get("phone_number", "").strip()
        if not phone_number:
            return HttpResponse("", status=200)

        try:
            phone_validator(phone_number)
            return HttpResponse("", status=200)
        except ValidationError as e:
            error_html = f'<div class="invalid-feedback d-block">{e.message}</div>'
            return HttpResponse(error_html, status=200)


class ValidateCNICView(View):
    def post(self, request):
        cnic = request.POST.get("cnic", "").strip()
        if not cnic:
            return HttpResponse("", status=200)

        try:
            cnic_validator(cnic)
            return HttpResponse("", status=200)
        except ValidationError as e:
            error_html = f'<div class="invalid-feedback d-block">{e.message}</div>'
            return HttpResponse(error_html, status=200)
