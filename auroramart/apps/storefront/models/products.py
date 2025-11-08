from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.text import slugify
from django.db.models import Q
from django.contrib.auth import get_user_model
from django.urls import reverse

class Category(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='categories/', blank=True, null=True)
    parent = models.ForeignKey('self', on_delete=models.CASCADE,
                               blank=True, null=True, related_name='children')
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'categories'
        verbose_name_plural = 'Categories'
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def get_all_products(self):
        """Get all products in this category and subcategories"""
        categories = [self]
        # Get all descendants
        children = list(self.children.all())
        while children:
            categories.extend(children)
            children = [child for cat in children for child in cat.children.all()]

        return Product.objects.filter(
            Q(category__in=categories) & Q(is_active=True)
        )


class Product(models.Model):
    # Identification
    sku = models.CharField(max_length=50, unique=True, db_index=True)
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)

    # Content
    description = models.TextField()
    category = models.ForeignKey(Category, on_delete=models.PROTECT,
                                 related_name='products')

    # Pricing
    price = models.DecimalField(max_digits=10, decimal_places=2,
                               validators=[MinValueValidator(0)])
    original_price = models.DecimalField(max_digits=10, decimal_places=2,
                                        validators=[MinValueValidator(0)],
                                        blank=True, null=True)

    # Inventory
    stock = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    reorder_threshold = models.IntegerField(default=10,
                                           validators=[MinValueValidator(0)])

    # Ratings
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0,
                                validators=[MinValueValidator(0), MaxValueValidator(5)])
    review_count = models.IntegerField(default=0, validators=[MinValueValidator(0)])

    # Status
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False,
                                      help_text="Show on homepage as featured")

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'products'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['category', '-created_at']),
            models.Index(fields=['-rating']),
            models.Index(fields=['is_active', 'stock']),
        ]

    def __str__(self):
        return self.name

    @property
    def is_in_stock(self):
        return self.stock > 0

    @property
    def is_low_stock(self):
        return 0 < self.stock <= self.reorder_threshold

    @property
    def stock_status(self):
        if not self.is_in_stock:
            return 'Out of Stock'
        elif self.is_low_stock:
            return 'Low Stock'
        return 'In Stock'

    @property
    def discount_percentage(self):
        if self.original_price and self.original_price > self.price:
            return round(((self.original_price - self.price) / self.original_price) * 100)
        return 0


class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE,
                               related_name='images')
    image = models.ImageField(upload_to='products/')
    alt_text = models.CharField(max_length=255, blank=True)
    is_primary = models.BooleanField(default=False)
    order = models.IntegerField(default=0)

    class Meta:
        db_table = 'product_images'
        ordering = ['-is_primary', 'order']

    def __str__(self):
        return f"{self.product.name} - Image {self.order}"

    def save(self, *args, **kwargs):
        # Ensure only one primary image per product
        if self.is_primary:
            ProductImage.objects.filter(product=self.product, is_primary=True)\
                .exclude(pk=self.pk).update(is_primary=False)
        super().save(*args, **kwargs)


class ProductSpecification(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE,
                               related_name='specifications')
    name = models.CharField(max_length=100)
    value = models.CharField(max_length=255)
    order = models.IntegerField(default=0)

    class Meta:
        db_table = 'product_specifications'
        ordering = ['order', 'name']

    def __str__(self):
        return f"{self.product.name} - {self.name}: {self.value}"

class BrowsingHistory(models.Model):
    """Track user browsing history for ML recommendations"""
    user = models.ForeignKey(
        'core.User',
        on_delete=models.CASCADE,
        related_name='browsing_history'
    )
    product = models.ForeignKey(
        'Product',
        on_delete=models.CASCADE,
        related_name='browsing_records'
    )
    viewed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-viewed_at']
        verbose_name_plural = 'Browsing Histories'
        indexes = [
            models.Index(fields=['user', '-viewed_at']),
            models.Index(fields=['product', '-viewed_at']),
        ]

    def __str__(self):
        return f"{self.user.username} viewed {self.product.name}"
