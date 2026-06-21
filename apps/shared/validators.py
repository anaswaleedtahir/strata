import string

from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator

phone_validator = RegexValidator(
    regex=r"^\+\d{2}-\d{10}$",
    message="Phone number must be in the format +92-3001234567 (country code + 10 digits)",
    code="invalid_phone",
)

cnic_validator = RegexValidator(
    regex=r"^\d{5}-\d{7}-\d$",
    message="CNIC must be in the format 12345-1234567-1",
    code="invalid_cnic",
)


def validate_password_strength(password: str):
    if len(password) < 8:
        raise ValidationError("Password must be at least 8 characters long.")
    if not any(char.isdigit() for char in password):
        raise ValidationError("Password must contain at least one digit.")
    if not any(char.isupper() for char in password):
        raise ValidationError("Password must contain at least one uppercase letter.")
    if not any(char in string.punctuation for char in password):
        raise ValidationError("Password must contain at least one special character.")
