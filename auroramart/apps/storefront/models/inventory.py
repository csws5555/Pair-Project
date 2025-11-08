from django.db import models
from django.conf import settings
from django.utils import timezone
from .products import Product


class StockMovement(models.Model):
    MOVEMENT_TYPE_CHOICES = [
        ('purchase', 'Purchase'),
        ('sale', 'Sale'),
        ('adjustment', 'Adjustment'),
        ('return', 'Return'),
    ]

    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name='stock_movements'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='stock_movements',
        help_text="User who made this stock change"
    )
    movement_type = models.CharField(
        max_length=20,
        choices=MOVEMENT_TYPE_CHOICES
    )
    quantity = models.IntegerField(
        help_text="Positive for stock increase, negative for decrease"
    )
    reason = models.TextField(
        help_text="Reason for this stock movement"
    )
    reference_number = models.CharField(
        max_length=100,
        blank=True,
        help_text="Order number, invoice number, etc."
    )
    created_at = models.DateTimeField(auto_now_add=True)

    # Stock level before and after for audit trail
    stock_before = models.IntegerField(default=0)
    stock_after = models.IntegerField(default=0)

    class Meta:
        db_table = 'stock_movements'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['product', '-created_at']),
            models.Index(fields=['movement_type', '-created_at']),
        ]

    def __str__(self):
        return (
            f"{self.get_movement_type_display()} - "
            f"{self.product.name} - "
            f"{self.quantity:+d} units"
        )

    def save(self, *args, **kwargs):
        """Record stock levels and update product stock"""
        # Record stock before
        self.stock_before = self.product.stock

        # Update product stock
        self.product.stock += self.quantity
        self.product.save()

        # Record stock after
        self.stock_after = self.product.stock

        super().save(*args, **kwargs)

        # Check if we need to create stock alerts
        self._check_stock_alerts()

    def _check_stock_alerts(self):
        """Create stock alerts if needed"""
        if self.product.stock <= 0:
            StockAlert.objects.get_or_create(
                product=self.product,
                alert_type='out_of_stock',
                is_resolved=False
            )
        elif self.product.stock <= self.product.reorder_threshold:
            StockAlert.objects.get_or_create(
                product=self.product,
                alert_type='low_stock',
                is_resolved=False
            )


class StockAlert(models.Model):
    ALERT_TYPE_CHOICES = [
        ('low_stock', 'Low Stock'),
        ('out_of_stock', 'Out of Stock'),
    ]

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='stock_alerts'
    )
    alert_type = models.CharField(
        max_length=20,
        choices=ALERT_TYPE_CHOICES
    )
    is_resolved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'stock_alerts'
        ordering = ['is_resolved', '-created_at']
        indexes = [
            models.Index(fields=['is_resolved', '-created_at']),
            models.Index(fields=['product', 'is_resolved']),
        ]

    def __str__(self):
        status = "Resolved" if self.is_resolved else "Active"
        return (
            f"{self.get_alert_type_display()} - "
            f"{self.product.name} ({status})"
        )

    def resolve(self):
        """Mark this alert as resolved"""
        if not self.is_resolved:
            self.is_resolved = True
            self.resolved_at = timezone.now()
            self.save()

    @property
    def days_active(self):
        """Calculate how many days this alert has been active"""
        end_time = self.resolved_at if self.is_resolved else timezone.now()
        delta = end_time - self.created_at
        return delta.days
