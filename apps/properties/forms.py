"""Forms for property-related operations."""

from django import forms
from django.core.validators import FileExtensionValidator

from apps.properties.models import Property


class PropertyForm(forms.ModelForm):
    """Form for creating and editing properties."""

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
            "property_type",
            "price",
            "bedrooms",
            "bathrooms",
            "area",
            "documents",
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
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["description"].required = False
        self.fields["bedrooms"].required = False
        self.fields["bathrooms"].required = False
        self.fields["area"].required = True
        self.fields["property_type"].choices = (
            ("", "Choose a property type"),
            *Property.PROPERTY_TYPE,
        )


class PropertyFilterForm(forms.Form):
    """Validate the public Property discovery query string."""

    SORT_CHOICES = (
        ("newest", "Newest"),
        ("price_asc", "Price: low to high"),
        ("price_desc", "Price: high to low"),
        ("oldest", "Oldest"),
    )

    q = forms.CharField(required=False, max_length=120, label="Search")
    property_type = forms.ChoiceField(
        required=False,
        choices=(("", "Any property type"), *Property.PROPERTY_TYPE),
        label="Property type",
    )
    min_price = forms.DecimalField(
        required=False, min_value=0, decimal_places=0, label="Minimum price"
    )
    max_price = forms.DecimalField(
        required=False, min_value=0, decimal_places=0, label="Maximum price"
    )
    bedrooms = forms.IntegerField(required=False, min_value=0, label="Bedrooms")
    bathrooms = forms.IntegerField(required=False, min_value=0, label="Bathrooms")
    sort = forms.ChoiceField(
        required=False, choices=SORT_CHOICES, initial="newest", label="Sort by"
    )

    def clean(self):
        cleaned_data = super().clean()
        min_price = cleaned_data.get("min_price")
        max_price = cleaned_data.get("max_price")
        if min_price is not None and max_price is not None and min_price > max_price:
            self.add_error("max_price", "Maximum price must be at least the minimum.")
        return cleaned_data
