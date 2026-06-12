from axes.handlers.proxy import AxesProxyHandler
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, logout, update_session_auth_hash
from django.contrib.auth import login as auth_login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views import View

from apps.shared.exceptions import ApplicationError
from apps.shared.mixins import HTMXMixin
from apps.users.forms import LoginForm, PasswordChangeForm, ProfileForm, SignupForm
from apps.users.selectors import user_get_by_email
from apps.users.services import user_create, user_password_change, user_update


class SignupView(HTMXMixin, View):
    def get(self, request):
        form = SignupForm()
        template = (
            "users/partials/signup_form.html" if self.is_htmx else "users/signup.html"
        )
        return render(request, template, {"form": form})

    def post(self, request):
        form = SignupForm(request.POST)

        if form.is_valid():
            try:
                user = user_create(
                    email=form.cleaned_data["email"],
                    password=form.cleaned_data["password1"],
                    first_name=form.cleaned_data["first_name"],
                    last_name=form.cleaned_data["last_name"],
                )
            except ApplicationError as e:
                form.add_error(None, e.message)
            else:
                auth_login(
                    request, user, backend="django.contrib.auth.backends.ModelBackend"
                )
                messages.success(
                    request,
                    f"Welcome to RealmKey, {user.first_name}! Your account has been created successfully.",
                )
                if self.is_htmx:
                    response = HttpResponse()
                    response["HX-Redirect"] = reverse("properties:list")
                    return response
                return redirect("properties:list")

        template = (
            "users/partials/signup_form.html" if self.is_htmx else "users/signup.html"
        )
        return render(request, template, {"form": form})


class LoginView(HTMXMixin, View):
    def _get_cooloff_message(self, prefix):
        cooloff_time = getattr(settings, "AXES_COOLOFF_TIME", None)
        if cooloff_time:
            cooloff_seconds = int(cooloff_time.total_seconds())
            if cooloff_seconds < 60:
                time_msg = f"{cooloff_seconds} seconds"
            elif cooloff_seconds < 3600:
                time_msg = f"{cooloff_seconds // 60} minutes"
            else:
                time_msg = f"{cooloff_seconds // 3600} hours"
            return f"{prefix} {time_msg}."
        return "Too many failed login attempts. Please contact support."

    def get(self, request):
        form = LoginForm()
        template = (
            "users/partials/login_form.html" if self.is_htmx else "users/login.html"
        )
        return render(request, template, {"form": form})

    def post(self, request):
        form = LoginForm(request.POST)
        template = (
            "users/partials/login_form.html" if self.is_htmx else "users/login.html"
        )

        if AxesProxyHandler.is_locked(request):
            error_msg = self._get_cooloff_message(
                "Too many failed login attempts. Please try again after"
            )
            form.add_error(None, error_msg)
            return render(request, template, {"form": form})

        if form.is_valid():
            email = form.cleaned_data["email"]
            password = form.cleaned_data["password"]
            user = authenticate(request, username=email, password=password)

            if user is not None:
                if user.is_active:
                    auth_login(
                        request,
                        user,
                        backend="django.contrib.auth.backends.ModelBackend",
                    )
                    messages.success(
                        request, f"Welcome back, {user.first_name or user.email}!"
                    )
                    if self.is_htmx:
                        response = HttpResponse()
                        response["HX-Redirect"] = reverse("properties:list")
                        return response
                    return redirect("properties:list")
                else:
                    form.add_error(None, "Your account has been disabled.")
            else:
                if AxesProxyHandler.is_locked(request):
                    error_msg = self._get_cooloff_message(
                        "Too many failed login attempts. Your account has been temporarily locked for"
                    )
                else:
                    error_msg = "Invalid email or password."
                form.add_error(None, error_msg)

        return render(request, template, {"form": form})


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
            except ApplicationError as e:
                form.add_error(None, e.message)
            else:
                messages.success(request, "Your profile has been updated successfully.")
                if self.is_htmx:
                    response = HttpResponse()
                    response["HX-Redirect"] = reverse("users:profile")
                    return response
                return redirect("users:profile")

        return render(request, template, {"form": form})


class PasswordChangeView(LoginRequiredMixin, View):
    def get(self, request):
        form = PasswordChangeForm()
        return render(request, "users/password_change.html", {"form": form})

    def post(self, request):
        form = PasswordChangeForm(request.POST)
        if form.is_valid():
            try:
                user_password_change(
                    user=request.user,
                    old_password=form.cleaned_data["old_password"],
                    new_password=form.cleaned_data["new_password1"],
                )
            except ApplicationError as e:
                form.add_error(None, e.message)
            else:
                update_session_auth_hash(request, request.user)
                messages.success(
                    request, "Your password has been changed successfully."
                )
                return redirect("users:profile")
        return render(request, "users/password_change.html", {"form": form})


class LogoutView(View):
    def post(self, request):
        logout(request)
        return redirect("properties:list")


class ValidateEmailView(View):
    def post(self, request):
        email = request.POST.get("email", "").strip().lower()

        if not email:
            return HttpResponse("", status=200)

        if user_get_by_email(email=email) is not None:
            error_html = '<div class="invalid-feedback d-block">This email address is already registered.</div>'
            return HttpResponse(error_html, status=200)

        return HttpResponse("", status=200)
