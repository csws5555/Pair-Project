from django.contrib import admin
from .models import (
    Category, Product, ProductImage, ProductSpecification, BrowsingHistory,
    Cart, CartItem,
    Order, OrderItem, Address,
    StockMovement, StockAlert,
    CustomerProfile, CustomerNote,
    CategoryPerformance, ProductPerformance
)

# Product models
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'parent', 'is_active']
    list_filter = ['is_active', 'parent']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['sku', 'name', 'category', 'price', 'stock', 'is_active', 'is_featured']
    list_filter = ['category', 'is_active', 'is_featured', 'created_at']
    search_fields = ['sku', 'name', 'description']
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ['created_at', 'updated_at']

@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ['product', 'is_primary', 'order']
    list_filter = ['is_primary']
    search_fields = ['product__name', 'alt_text']

@admin.register(ProductSpecification)
class ProductSpecificationAdmin(admin.ModelAdmin):
    list_display = ['product', 'name', 'value', 'order']
    search_fields = ['product__name', 'name', 'value']

@admin.register(BrowsingHistory)
class BrowsingHistoryAdmin(admin.ModelAdmin):
    list_display = ['user', 'product', 'viewed_at']
    list_filter = ['viewed_at']
    search_fields = ['user__username', 'product__name']
    readonly_fields = ['viewed_at']

# Cart models
@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ['user', 'created_at', 'updated_at']
    search_fields = ['user__username']
    readonly_fields = ['created_at', 'updated_at']

@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ['cart', 'product', 'quantity', 'added_at']
    search_fields = ['cart__user__username', 'product__name']
    readonly_fields = ['added_at']

# Order models
@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['order_number', 'user', 'status', 'total', 'created_at']
    list_filter = ['status', 'payment_method', 'created_at']
    search_fields = ['order_number', 'user__username', 'user__email']
    readonly_fields = ['order_number', 'created_at', 'updated_at']

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ['order', 'product_name', 'quantity', 'price']
    search_fields = ['order__order_number', 'product_name', 'product_sku']

@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ['user', 'address_type', 'city', 'state', 'is_default']
    list_filter = ['address_type', 'is_default']
    search_fields = ['user__username', 'name', 'city', 'state']

# Inventory models
@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ['product', 'movement_type', 'quantity', 'stock_before', 'stock_after', 'created_at']
    list_filter = ['movement_type', 'created_at']
    search_fields = ['product__name', 'reference_number']
    readonly_fields = ['created_at', 'stock_before', 'stock_after']

@admin.register(StockAlert)
class StockAlertAdmin(admin.ModelAdmin):
    list_display = ['product', 'alert_type', 'is_resolved', 'created_at', 'resolved_at']
    list_filter = ['alert_type', 'is_resolved', 'created_at']
    search_fields = ['product__name']
    readonly_fields = ['created_at']

# Customer models
@admin.register(CustomerProfile)
class CustomerProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'customer_tier', 'total_spent', 'order_count', 'customer_since']
    list_filter = ['customer_since']
    search_fields = ['user__username', 'user__email']
    readonly_fields = ['customer_since']

@admin.register(CustomerNote)
class CustomerNoteAdmin(admin.ModelAdmin):
    list_display = ['customer', 'admin', 'created_at']
    search_fields = ['customer__username', 'admin__username', 'note']
    readonly_fields = ['created_at']

# Analytics models
@admin.register(CategoryPerformance)
class CategoryPerformanceAdmin(admin.ModelAdmin):
    list_display = ['category', 'period_start', 'period_end', 'total_sales', 'total_orders']
    list_filter = ['period_start', 'period_end']
    search_fields = ['category__name']
    readonly_fields = ['generated_at']

@admin.register(ProductPerformance)
class ProductPerformanceAdmin(admin.ModelAdmin):
    list_display = ['product', 'period_start', 'period_end', 'total_sales', 'total_orders', 'views']
    list_filter = ['period_start', 'period_end']
    search_fields = ['product__name']
    readonly_fields = ['generated_at']
