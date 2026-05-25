"""Forms for property-related operations."""

from django import forms
from django.core.validators import FileExtensionValidator

from apps.properties.models import Property
from apps.shared.validators import cnic_validator, phone_validator


class PropertyForm(forms.ModelForm):
    """Form for creating and editing properties."""

    phone_number = forms.CharField(
        max_length=16,
        validators=[phone_validator],
        help_text="Format: +92-3001234567",
        label="Phone Number",
    )

    cnic = forms.CharField(
        max_length=15,
        validators=[cnic_validator],
        help_text="Format: 12345-1234567-1",
        label="CNIC",
    )

    documents = forms.FileField(
        required=False,
        validators=[FileExtensionValidator(allowed_extensions=["pdf"])],
        widget=forms.FileInput(attrs={"accept": ".pdf"}),
        label="Documents (PDF)",
        help_text="Upload property documents (PDF only, max 10MB)",
    )

    class Meta:
        model = Property
        fields = [
            "name",
            "description",
            "full_address",
            "phone_number",
            "cnic",
            "property_type",
            "price",
            "bedrooms",
            "bathrooms",
            "area",
            "documents",
            "is_published",
        ]
        widgets = {
            "name": forms.TextInput(),
            "description": forms.Textarea(),
            "full_address": forms.TextInput(),
            "property_type": forms.Select(),
            "price": forms.NumberInput(attrs={"step": "0.01", "min": "0"}),
            "bedrooms": forms.NumberInput(attrs={"min": "0"}),
            "bathrooms": forms.NumberInput(attrs={"min": "0"}),
            "area": forms.NumberInput(attrs={"step": "0.01", "min": "0"}),
            "is_published": forms.CheckboxInput(),
        }
        labels = {
            "name": "Property Name",
            "description": "Description",
            "full_address": "Full Address",
            "property_type": "Property Type",
            "price": "Price",
            "bedrooms": "Bedrooms",
            "bathrooms": "Bathrooms",
            "area": "Area (sq ft)",
            "is_published": "Publish Property",
        }
        help_texts = {
            "is_published": "Make this property visible to other users",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["description"].required = False
        self.fields["bedrooms"].required = True
        self.fields["bathrooms"].required = True
        self.fields["area"].required = True
        if not self.instance.pk:
            self.fields["is_published"].initial = False
