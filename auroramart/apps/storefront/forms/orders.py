"""
Order forms for checkout process
"""
from django import forms
from django.core.validators import RegexValidator
from ..models import Address


class ShippingAddressForm(forms.ModelForm):
    """Form for shipping address during checkout"""

    use_different_billing = forms.BooleanField(
        required=False,
        initial=False,
        label='Use a different billing address',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    save_address = forms.BooleanField(
        required=False,
        initial=False,
        label='Save this address for future orders',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    phone = forms.CharField(
        max_length=20,
        required=True,
        validators=[
            RegexValidator(
                regex=r'^\+?1?\d{9,15}$',
                message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."
            )
        ],
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '+1234567890'
        })
    )

    class Meta:
        model = Address
        fields = ['name', 'phone', 'line1', 'line2', 'city', 'state', 'postal_code', 'country']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'John Doe'}),
            'line1': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '123 Main Street'}),
            'line2': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Apartment, suite, etc. (optional)'}),
            'city': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'City'}),
            'state': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'State/Province'}),
            'postal_code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '12345'}),
            'country': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Country', 'value': 'USA'}),
        }
        labels = {
            'name': 'Full Name',
            'line1': 'Address Line 1',
            'line2': 'Address Line 2',
            'city': 'City',
            'state': 'State/Province',
            'postal_code': 'Postal Code',
            'country': 'Country',
        }


class BillingAddressForm(forms.ModelForm):
    """Form for billing address during checkout"""

    save_address = forms.BooleanField(
        required=False,
        initial=False,
        label='Save this address for future orders',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    phone = forms.CharField(
        max_length=20,
        required=True,
        validators=[
            RegexValidator(
                regex=r'^\+?1?\d{9,15}$',
                message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."
            )
        ],
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '+1234567890'
        })
    )

    class Meta:
        model = Address
        fields = ['name', 'phone', 'line1', 'line2', 'city', 'state', 'postal_code', 'country']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'John Doe'}),
            'line1': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '123 Main Street'}),
            'line2': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Apartment, suite, etc. (optional)'}),
            'city': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'City'}),
            'state': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'State/Province'}),
            'postal_code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '12345'}),
            'country': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Country', 'value': 'USA'}),
        }
        labels = {
            'name': 'Full Name',
            'line1': 'Address Line 1',
            'line2': 'Address Line 2',
            'city': 'City',
            'state': 'State/Province',
            'postal_code': 'Postal Code',
            'country': 'Country',
        }


class PaymentMethodForm(forms.Form):
    """Form for payment method during checkout"""

    card_name = forms.CharField(
        max_length=255,
        required=True,
        label='Cardholder Name',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'John Doe'
        })
    )

    card_number = forms.CharField(
        max_length=19,
        required=True,
        label='Card Number',
        validators=[
            RegexValidator(
                regex=r'^\d{13,19}$',
                message="Please enter a valid card number (13-19 digits)"
            )
        ],
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '1234 5678 9012 3456',
            'maxlength': '19'
        })
    )

    expiry_month = forms.ChoiceField(
        choices=[(str(i).zfill(2), str(i).zfill(2)) for i in range(1, 13)],
        required=True,
        label='Expiry Month',
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    expiry_year = forms.ChoiceField(
        choices=[(str(i), str(i)) for i in range(2024, 2035)],
        required=True,
        label='Expiry Year',
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    cvv = forms.CharField(
        max_length=4,
        required=True,
        label='CVV',
        validators=[
            RegexValidator(
                regex=r'^\d{3,4}$',
                message="Please enter a valid CVV (3-4 digits)"
            )
        ],
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': '123',
            'maxlength': '4'
        })
    )

    save_payment_method = forms.BooleanField(
        required=False,
        initial=False,
        label='Save this payment method for future orders',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )


class OrderReviewForm(forms.Form):
    """Form for order review - terms and conditions acceptance"""

    accept_terms = forms.BooleanField(
        required=True,
        label='I accept the terms and conditions',
        error_messages={
            'required': 'You must accept the terms and conditions to place your order'
        },
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
