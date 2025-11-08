from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from django.utils import timezone
from .products import Category


class CustomerProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='customer_profile'
    )
    notes = models.TextField(
        blank=True,
        help_text="Admin notes about this customer"
    )
    preferred_category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='preferred_by_customers',
        help_text="Customer's preferred product category"
    )
    customer_since = models.DateField(auto_now_add=True)
    last_purchase_date = models.DateField(null=True, blank=True)
    total_spent = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)]
    )
    order_count = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'customer_profiles'
        ordering = ['-customer_since']

    def __str__(self):
        return f"Profile for {self.user.username}"

    def update_stats(self):
        """Recalculate customer statistics from orders"""
        from .orders import Order
        from django.db.models import Sum, Count, Max

        # Get all completed orders for this customer
        orders = Order.objects.filter(
            user=self.user,
            status__in=['delivered', 'processing', 'shipped']
        )

        # Calculate statistics
        stats = orders.aggregate(
            total_spent=Sum('total'),
            order_count=Count('id'),
            last_purchase=Max('created_at')
        )

        # Update fields
        self.total_spent = stats['total_spent'] or 0
        self.order_count = stats['order_count'] or 0

        if stats['last_purchase']:
            self.last_purchase_date = stats['last_purchase'].date()

        self.save()

    @property
    def average_order_value(self):
        """Calculate average order value"""
        if self.order_count > 0:
            return self.total_spent / self.order_count
        return 0

    @property
    def customer_tier(self):
        """Determine customer tier based on total spent"""
        if self.total_spent >= 10000:
            return 'Platinum'
        elif self.total_spent >= 5000:
            return 'Gold'
        elif self.total_spent >= 1000:
            return 'Silver'
        return 'Bronze'


class CustomerNote(models.Model):
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='customer_notes',
        help_text="The customer this note is about"
    )
    admin = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='admin_notes',
        help_text="The admin who wrote this note"
    )
    note = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'customer_notes'
        ordering = ['-created_at']

    def __str__(self):
        return f"Note for {self.customer.username} by {self.admin.username if self.admin else 'Unknown'}"
