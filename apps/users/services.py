from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from apps.shared.exceptions import ApplicationError
from apps.shared.validators import validate_password_strength

User = get_user_model()


def _check_password_strength(password: str) -> None:
    try:
        validate_password_strength(password)
    except ValidationError as e:
        raise ApplicationError(e.message) from e


def user_create(
    *,
    email: str,
    password: str | None,
    first_name: str,
    last_name: str,
    user=None,
) -> User:
    email = email.strip().lower()

    email_query = User.objects.filter(email=email)
    if user is not None and user.pk:
        email_query = email_query.exclude(pk=user.pk)
    if email_query.exists():
        raise ApplicationError("This email address is already registered.")

    if password:
        _check_password_strength(password)

    user = user or User()
    user.email = email
    user.first_name = first_name
    user.last_name = last_name
    if password:
        user.set_password(password)
    else:
        user.set_unusable_password()
    user.full_clean()
    user.save()
    return user


def user_update(*, user: User, first_name: str, last_name: str, email: str) -> User:
    email = email.strip().lower()

    if User.objects.filter(email=email).exclude(pk=user.pk).exists():
        raise ApplicationError("This email address is already registered.")

    user.first_name = first_name
    user.last_name = last_name
    user.email = email
    user.full_clean()
    user.save(update_fields=["first_name", "last_name", "email"])
    return user
