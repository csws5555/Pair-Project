from django.contrib import admin
from .models import Order, OrderItem, Address


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    fields = ['product', 'product_name', 'product_sku', 'price', 'quantity', 'total_price']
    readonly_fields = ['product_name', 'product_sku', 'price', 'total_price']
    can_delete = False
    
    def total_price(self, obj):
        return f"${obj.total_price:.2f}" if obj.id else "-"
    total_price.short_description = 'Total Price'


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['order_number', 'user', 'status', 'total', 'created_at']
    list_filter = ['status', 'payment_method', 'created_at']
    search_fields = ['order_number', 'user__username', 'user__email', 
                    'shipping_name', 'billing_name']
    readonly_fields = ['order_number', 'created_at', 'updated_at']
    inlines = [OrderItemInline]
    
    fieldsets = (
        ('Order Information', {
            'fields': ('order_number', 'user', 'status', 'created_at', 'updated_at')
        }),
        ('Shipping Address', {
            'fields': (
                'shipping_name', 'shipping_line1', 'shipping_line2',
                'shipping_city', 'shipping_state', 'shipping_postal_code',
                'shipping_country'
            ),
            'classes': ('collapse',)
        }),
        ('Billing Address', {
            'fields': (
                'billing_name', 'billing_line1', 'billing_line2',
                'billing_city', 'billing_state', 'billing_postal_code',
                'billing_country'
            ),
            'classes': ('collapse',)
        }),
        ('Payment', {
            'fields': ('payment_method', 'payment_transaction_id')
        }),
        ('Pricing', {
            'fields': ('subtotal', 'tax', 'shipping_cost', 'total')
        }),
        ('Delivery', {
            'fields': ('estimated_delivery',)
        }),
    )


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ['order', 'product_name', 'product_sku', 'price', 'quantity', 'get_total_price']
    list_filter = ['order__status', 'order__created_at']
    search_fields = ['product_name', 'product_sku', 'order__order_number']
    readonly_fields = ['product_name', 'product_sku', 'price']
    
    def get_total_price(self, obj):
        return f"${obj.total_price:.2f}"
    get_total_price.short_description = 'Total Price'


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'address_type', 'city', 'state', 
                   'country', 'is_default']
    list_filter = ['address_type', 'is_default', 'country', 'state']
    search_fields = ['name', 'user__username', 'city', 'postal_code']
    
    fieldsets = (
        ('User Information', {
            'fields': ('user', 'address_type', 'is_default')
        }),
        ('Address Details', {
            'fields': (
                'name', 'line1', 'line2', 'city', 
                'state', 'postal_code', 'country'
            )
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ['created_at', 'updated_at']