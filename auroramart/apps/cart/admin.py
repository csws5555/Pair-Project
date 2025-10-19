from django.contrib import admin
from .models import Cart, CartItem


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    fields = ['product', 'quantity', 'total_price', 'added_at']
    readonly_fields = ['total_price', 'added_at']
    
    def total_price(self, obj):
        return f"${obj.total_price:.2f}" if obj.id else "-"
    total_price.short_description = 'Total Price'


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ['user', 'total_items', 'subtotal', 'updated_at']
    search_fields = ['user__username', 'user__email']
    readonly_fields = ['created_at', 'updated_at', 'total_items', 'subtotal']
    inlines = [CartItemInline]
    
    def total_items(self, obj):
        return obj.total_items
    total_items.short_description = 'Total Items'
    
    def subtotal(self, obj):
        return f"${obj.subtotal:.2f}"
    subtotal.short_description = 'Subtotal'


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ['cart', 'product', 'quantity', 'total_price', 'added_at']
    list_filter = ['added_at', 'cart__user']
    search_fields = ['product__name', 'cart__user__username']
    readonly_fields = ['added_at']
    
    def total_price(self, obj):
        return f"${obj.total_price:.2f}"
    total_price.short_description = 'Total Price'