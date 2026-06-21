from allauth.account.adapter import DefaultAccountAdapter
from django.core.exceptions import ValidationError

from apps.shared.validators import validate_password_strength
from apps.users.services import user_create


class StrataAccountAdapter(DefaultAccountAdapter):
    def clean_password(self, password, user=None):
        default_error = None
        try:
            password = super().clean_password(password, user=user)
        except ValidationError as error:
            default_error = error

        try:
            validate_password_strength(password)
        except ValidationError as error:
            raise error from default_error

        if default_error:
            raise default_error

        return password

    def save_user(self, request, user, form, commit=True):
        data = form.cleaned_data
        password = data.get("password1") or data.get("password")
        if commit:
            return user_create(
                email=data.get("email", ""),
                password=password,
                first_name=data.get("first_name", ""),
                last_name=data.get("last_name", ""),
                user=user,
            )

        user.email = data.get("email", "").strip().lower()
        user.first_name = data.get("first_name", "")
        user.last_name = data.get("last_name", "")
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        return user
