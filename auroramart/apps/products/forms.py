"""
Product forms
"""
from django import forms
from django.forms import inlineformset_factory
from .models import Product, ProductImage, ProductSpecification


class ProductForm(forms.ModelForm):
    """Form for creating/editing products"""

    class Meta:
        model = Product
        fields = [
            'sku', 'name', 'slug', 'description', 'category',
            'price', 'original_price', 'stock', 'reorder_threshold',
            'is_active', 'is_featured'
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
        }


# Inline formsets for images and specifications
ProductImageFormSet = inlineformset_factory(
    Product,
    ProductImage,
    fields=('image', 'alt_text', 'is_primary', 'order'),
    extra=1,
    can_delete=True
)

ProductSpecificationFormSet = inlineformset_factory(
    Product,
    ProductSpecification,
    fields=('name', 'value', 'order'),
    extra=1,
    can_delete=True
)


class ProductImportForm(forms.Form):
    """Form for importing products from CSV"""
    csv_file = forms.FileField(
        label='CSV File',
        help_text='Upload a CSV file with product data'
    )
