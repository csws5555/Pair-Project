import uuid
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from .products import Product
from django.contrib.auth import get_user_model

User = get_user_model()


class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ]

    PAYMENT_METHOD_CHOICES = [
        ('credit_card', 'Credit Card'),
        ('debit_card', 'Debit Card'),
        ('paypal', 'PayPal'),
        ('bank_transfer', 'Bank Transfer'),
        ('cash_on_delivery', 'Cash on Delivery'),
    ]

    # Order Identification
    order_number = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
        db_index=True
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='orders'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        db_index=True
    )

    # Shipping Address
    shipping_name = models.CharField(max_length=255)
    shipping_line1 = models.CharField(max_length=255)
    shipping_line2 = models.CharField(max_length=255, blank=True)
    shipping_city = models.CharField(max_length=100)
    shipping_state = models.CharField(max_length=100)
    shipping_postal_code = models.CharField(max_length=20)
    shipping_country = models.CharField(max_length=100)

    # Billing Address
    billing_name = models.CharField(max_length=255)
    billing_line1 = models.CharField(max_length=255)
    billing_line2 = models.CharField(max_length=255, blank=True)
    billing_city = models.CharField(max_length=100)
    billing_state = models.CharField(max_length=100)
    billing_postal_code = models.CharField(max_length=20)
    billing_country = models.CharField(max_length=100)

    # Payment Information
    payment_method = models.CharField(
        max_length=50,
        choices=PAYMENT_METHOD_CHOICES
    )
    payment_transaction_id = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )

    # Pricing
    subtotal = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    tax = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        default=0
    )
    shipping_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        default=0
    )
    total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    estimated_delivery = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = 'orders'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['-created_at']),
        ]

    def __str__(self):
        return f"Order {self.order_number} - {self.user.username}"

    @property
    def shipping_address(self):
        """Get formatted shipping address"""
        address = f"{self.shipping_name}\n{self.shipping_line1}\n"
        if self.shipping_line2:
            address += f"{self.shipping_line2}\n"
        address += f"{self.shipping_city}, {self.shipping_state} {self.shipping_postal_code}\n"
        address += f"{self.shipping_country}"
        return address

    @property
    def billing_address(self):
        """Get formatted billing address"""
        address = f"{self.billing_name}\n{self.billing_line1}\n"
        if self.billing_line2:
            address += f"{self.billing_line2}\n"
        address += f"{self.billing_city}, {self.billing_state} {self.billing_postal_code}\n"
        address += f"{self.billing_country}"
        return address


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name='order_items'
    )

    # Snapshot fields (preserve order history)
    product_name = models.CharField(max_length=255)
    product_sku = models.CharField(max_length=50)
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )

    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        db_table = 'order_items'
        ordering = ['id']

    def __str__(self):
        return f"{self.quantity}x {self.product_name} (Order {self.order.order_number})"

    @property
    def total_price(self):
        """Calculate total price for this order item"""
        return self.quantity * self.price

    def save(self, *args, **kwargs):
        """Snapshot product data on first save"""
        if not self.pk:  # Only on creation
            self.product_name = self.product.name
            self.product_sku = self.product.sku
            self.price = self.product.price
        super().save(*args, **kwargs)


class Address(models.Model):
    ADDRESS_TYPE_CHOICES = [
        ('shipping', 'Shipping'),
        ('billing', 'Billing'),
        ('both', 'Both'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='addresses'
    )
    address_type = models.CharField(
        max_length=20,
        choices=ADDRESS_TYPE_CHOICES,
        default='both'
    )

    # Address Fields
    name = models.CharField(max_length=255)
    line1 = models.CharField(max_length=255)
    line2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    country = models.CharField(max_length=100)

    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'addresses'
        verbose_name_plural = 'Addresses'
        ordering = ['-is_default', '-created_at']

    def __str__(self):
        return f"{self.name} - {self.address_type} ({self.user.username})"

    def save(self, *args, **kwargs):
        """Ensure only one default address per type per user"""
        if self.is_default:
            # Remove default status from other addresses of same type
            Address.objects.filter(
                user=self.user,
                address_type=self.address_type,
                is_default=True
            ).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)

    @property
    def formatted_address(self):
        """Get formatted address string"""
        address = f"{self.name}\n{self.line1}\n"
        if self.line2:
            address += f"{self.line2}\n"
        address += f"{self.city}, {self.state} {self.postal_code}\n"
        address += f"{self.country}"
        return address
