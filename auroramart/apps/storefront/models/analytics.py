from django.db import models
from .products import Product, Category


class CategoryPerformance(models.Model):
    """Pre-computed analytics for category performance"""
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name='performance_metrics'
    )
    period_start = models.DateField()
    period_end = models.DateField()
    total_sales = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )
    total_orders = models.IntegerField(default=0)
    total_items_sold = models.IntegerField(default=0)
    average_order_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )
    generated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [['category', 'period_start', 'period_end']]
        indexes = [
            models.Index(fields=['period_start', 'period_end']),
            models.Index(fields=['category', '-period_start']),
            models.Index(fields=['-generated_at']),
        ]
        ordering = ['-period_start']
        verbose_name = "Category Performance"
        verbose_name_plural = "Category Performance Metrics"

    def __str__(self):
        return f"{self.category.name} ({self.period_start} to {self.period_end})"


class ProductPerformance(models.Model):
    """Pre-computed analytics for product performance"""
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='performance_metrics'
    )
    period_start = models.DateField()
    period_end = models.DateField()
    total_sales = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )
    total_orders = models.IntegerField(default=0)
    total_items_sold = models.IntegerField(default=0)
    average_order_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )
    views = models.IntegerField(
        default=0,
        help_text="Total product views from browsing history"
    )
    generated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [['product', 'period_start', 'period_end']]
        indexes = [
            models.Index(fields=['period_start', 'period_end']),
            models.Index(fields=['product', '-period_start']),
            models.Index(fields=['-generated_at']),
            models.Index(fields=['-total_sales']),
            models.Index(fields=['-views']),
        ]
        ordering = ['-period_start']
        verbose_name = "Product Performance"
        verbose_name_plural = "Product Performance Metrics"

    def __str__(self):
        return f"{self.product.name} ({self.period_start} to {self.period_end})"
