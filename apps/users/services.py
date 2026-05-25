from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from apps.shared.exceptions import ApplicationError
from apps.shared.services import model_update
from apps.shared.validators import validate_password_strength

User = get_user_model()


def user_create(*, email: str, password: str, first_name: str, last_name: str) -> User:
    email = email.strip().lower()

    if User.objects.filter(email=email).exists():
        raise ApplicationError("This email address is already registered.")

    try:
        validate_password_strength(password)
    except ValidationError as e:
        raise ApplicationError(e.message) from e

    user = User.objects.create_user(
        email=email,
        password=password,
        first_name=first_name,
        last_name=last_name,
    )
    return user


def user_password_change(*, user: User, old_password: str, new_password: str) -> None:
    if not user.check_password(old_password):
        raise ApplicationError("Current password is incorrect.")

    try:
        validate_password_strength(new_password)
    except ValidationError as e:
        raise ApplicationError(e.message) from e

    user.set_password(new_password)
    user.save(update_fields=["password"])


def user_update(*, user: User, first_name: str, last_name: str, email: str) -> User:
    email = email.strip().lower()

    if User.objects.filter(email=email).exclude(pk=user.pk).exists():
        raise ApplicationError("This email address is already registered.")

    return model_update(
        instance=user,
        fields=["first_name", "last_name", "email"],
        data={"first_name": first_name, "last_name": last_name, "email": email},
    )
