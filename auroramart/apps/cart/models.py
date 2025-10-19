from django.db import models
from django.conf import settings
from django.db.models import Sum, F
from django.core.exceptions import ValidationError
from apps.products.models import Product


class Cart(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='cart'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'carts'
        ordering = ['-updated_at']
    
    def __str__(self):
        return f"Cart for {self.user.username}"
    
    @property
    def total_items(self):
        """Calculate total number of items in cart"""
        return self.items.aggregate(
            total=Sum('quantity')
        )['total'] or 0
    
    @property
    def subtotal(self):
        """Calculate cart subtotal"""
        return sum(item.total_price for item in self.items.all())
    
    def clear(self):
        """Remove all items from cart"""
        self.items.all().delete()


class CartItem(models.Model):
    cart = models.ForeignKey(
        Cart,
        on_delete=models.CASCADE,
        related_name='items'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='cart_items'
    )
    quantity = models.PositiveIntegerField(default=1)
    added_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'cart_items'
        unique_together = ('cart', 'product')
        ordering = ['-added_at']
    
    def __str__(self):
        return f"{self.quantity}x {self.product.name} in {self.cart.user.username}'s cart"
    
    @property
    def total_price(self):
        """Calculate total price for this cart item"""
        return self.quantity * self.product.price
    
    def save(self, *args, **kwargs):
        """Validate stock availability before saving"""
        # Check if product is active
        if not self.product.is_active:
            raise ValidationError(f"{self.product.name} is not available for purchase.")
        
        # Check stock availability
        if self.quantity > self.product.stock:
            raise ValidationError(
                f"Only {self.product.stock} units of {self.product.name} available in stock."
            )
        
        # Ensure quantity is at least 1
        if self.quantity < 1:
            raise ValidationError("Quantity must be at least 1.")
        
        super().save(*args, **kwargs)
    
    def clean(self):
        """Additional validation"""
        if self.product and self.quantity > self.product.stock:
            raise ValidationError({
                'quantity': f'Only {self.product.stock} units available.'
            })