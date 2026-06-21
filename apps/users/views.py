from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views import View
from django_htmx.http import HttpResponseClientRedirect

from apps.shared.exceptions import ApplicationError
from apps.shared.mixins import HTMXMixin
from apps.users.forms import ProfileForm
from apps.users.services import user_update


class ProfileView(LoginRequiredMixin, View):
    def get(self, request):
        return render(request, "users/profile.html")


class ProfileEditView(LoginRequiredMixin, HTMXMixin, View):
    def get(self, request):
        form = ProfileForm(
            initial={
                "first_name": request.user.first_name,
                "last_name": request.user.last_name,
                "email": request.user.email,
            },
            user=request.user,
        )
        template = (
            "users/partials/profile_form.html" if self.is_htmx else "users/profile.html"
        )
        return render(request, template, {"form": form})

    def post(self, request):
        form = ProfileForm(request.POST, user=request.user)
        template = (
            "users/partials/profile_form.html" if self.is_htmx else "users/profile.html"
        )

        if form.is_valid():
            try:
                user_update(
                    user=request.user,
                    first_name=form.cleaned_data["first_name"],
                    last_name=form.cleaned_data["last_name"],
                    email=form.cleaned_data["email"],
                )
            except ApplicationError as error:
                form.add_error(None, error.message)
            else:
                messages.success(request, "Your profile has been updated successfully.")
                if self.is_htmx:
                    return HttpResponseClientRedirect(reverse("users:profile"))
                return redirect("users:profile")

        return render(request, template, {"form": form})
