from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from .models import StockMovement, StockAlert


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = [
        'product', 'movement_type', 'get_quantity_display', 
        'stock_before', 'stock_after', 'user', 'created_at'
    ]
    list_filter = [
        'movement_type', 'created_at', 'user'
    ]
    search_fields = [
        'product__name', 'product__sku', 
        'reference_number', 'reason'
    ]
    readonly_fields = [
        'stock_before', 'stock_after', 'created_at'
    ]
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Movement Information', {
            'fields': (
                'product', 'movement_type', 'quantity', 
                'user', 'reference_number'
            )
        }),
        ('Details', {
            'fields': ('reason',)
        }),
        ('Stock Levels', {
            'fields': ('stock_before', 'stock_after'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def get_quantity_display(self, obj):
        """Display quantity with color coding"""
        if obj.quantity > 0:
            color = 'green'
            symbol = '+'
        else:
            color = 'red'
            symbol = ''
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}{}</span>',
            color, symbol, obj.quantity
        )
    get_quantity_display.short_description = 'Quantity'
    get_quantity_display.admin_order_field = 'quantity'
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Auto-populate user field with current user"""
        if db_field.name == 'user':
            kwargs['initial'] = request.user
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(StockAlert)
class StockAlertAdmin(admin.ModelAdmin):
    list_display = [
        'product', 'alert_type', 'get_status_display', 
        'get_current_stock', 'days_active', 'created_at'
    ]
    list_filter = [
        'is_resolved', 'alert_type', 'created_at'
    ]
    search_fields = [
        'product__name', 'product__sku'
    ]
    readonly_fields = [
        'created_at', 'resolved_at', 'days_active'
    ]
    actions = ['resolve_alerts', 'unresolve_alerts']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Alert Information', {
            'fields': ('product', 'alert_type', 'is_resolved')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'resolved_at', 'days_active'),
            'classes': ('collapse',)
        }),
    )
    
    def get_status_display(self, obj):
        """Display status with color coding"""
        if obj.is_resolved:
            return format_html(
                '<span style="background-color: #28a745; color: white; '
                'padding: 3px 10px; border-radius: 3px;">Resolved</span>'
            )
        else:
            return format_html(
                '<span style="background-color: #dc3545; color: white; '
                'padding: 3px 10px; border-radius: 3px;">Active</span>'
            )
    get_status_display.short_description = 'Status'
    
    def get_current_stock(self, obj):
        """Display current stock level"""
        stock = obj.product.stock
        if stock <= 0:
            color = 'red'
        elif stock <= obj.product.reorder_threshold:
            color = 'orange'
        else:
            color = 'green'
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, stock
        )
    get_current_stock.short_description = 'Current Stock'
    
    def resolve_alerts(self, request, queryset):
        """Bulk action to resolve multiple alerts"""
        count = queryset.filter(is_resolved=False).count()
        for alert in queryset.filter(is_resolved=False):
            alert.resolve()
        
        self.message_user(
            request,
            f'Successfully resolved {count} alert(s).'
        )
    resolve_alerts.short_description = 'Resolve selected alerts'
    
    def unresolve_alerts(self, request, queryset):
        """Bulk action to unresolve alerts"""
        count = queryset.filter(is_resolved=True).update(
            is_resolved=False,
            resolved_at=None
        )
        
        self.message_user(
            request,
            f'Successfully unresolved {count} alert(s).'
        )
    unresolve_alerts.short_description = 'Unresolve selected alerts'