from django import forms
from django.core.exceptions import ValidationError


class LoginForm(forms.Form):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={"autocomplete": "email"}),
        error_messages={
            "required": "Email is required.",
            "invalid": "Enter a valid email address.",
        },
    )

    password = forms.CharField(
        required=True,
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}),
        error_messages={
            "required": "Password is required.",
        },
    )

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if email:
            email = email.strip().lower()
        return email


class SignupForm(forms.Form):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={"autocomplete": "email"}),
        error_messages={
            "required": "Email is required.",
            "invalid": "Enter a valid email address.",
        },
    )

    first_name = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={"autocomplete": "given-name"}),
        error_messages={
            "required": "First name is required.",
        },
    )

    last_name = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={"autocomplete": "family-name"}),
        error_messages={
            "required": "Last name is required.",
        },
    )

    password1 = forms.CharField(
        required=True,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        error_messages={
            "required": "Password is required.",
        },
    )

    password2 = forms.CharField(
        required=True,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        error_messages={
            "required": "Password confirmation is required.",
        },
        label="Confirm Password",
    )

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if email:
            email = email.strip().lower()
        return email

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")

        if password1 and password2 and password1 != password2:
            raise ValidationError({"password2": "Passwords do not match."})

        return cleaned_data


class ProfileForm(forms.Form):
    first_name = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={"autocomplete": "given-name"}),
        error_messages={
            "required": "First name is required.",
        },
    )

    last_name = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={"autocomplete": "family-name"}),
        error_messages={
            "required": "Last name is required.",
        },
    )

    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={"autocomplete": "email"}),
        error_messages={
            "required": "Email is required.",
            "invalid": "Enter a valid email address.",
        },
    )

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if email:
            email = email.strip().lower()
        return email


class PasswordChangeForm(forms.Form):
    old_password = forms.CharField(
        required=True,
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}),
        error_messages={"required": "Current password is required."},
        label="Current Password",
    )

    new_password1 = forms.CharField(
        required=True,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        error_messages={"required": "New password is required."},
        label="New Password",
    )

    new_password2 = forms.CharField(
        required=True,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        error_messages={"required": "Password confirmation is required."},
        label="Confirm New Password",
    )

    def clean(self):
        cleaned_data = super().clean()
        new_password1 = cleaned_data.get("new_password1")
        new_password2 = cleaned_data.get("new_password2")
        if new_password1 and new_password2 and new_password1 != new_password2:
            raise ValidationError({"new_password2": "Passwords do not match."})
        return cleaned_data
