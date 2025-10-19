from django.contrib import admin
from django.utils.html import format_html
from .models import CategoryPerformance, ProductPerformance


@admin.register(CategoryPerformance)
class CategoryPerformanceAdmin(admin.ModelAdmin):
    list_display = [
        'category',
        'period_start',
        'period_end',
        'formatted_total_sales',
        'total_orders',
        'total_items_sold',
        'formatted_avg_order_value',
        'generated_at'
    ]
    list_filter = [
        'period_start',
        'period_end',
        'generated_at',
        'category',
    ]
    search_fields = [
        'category__name',
    ]
    readonly_fields = [
        'category',
        'period_start',
        'period_end',
        'total_sales',
        'total_orders',
        'total_items_sold',
        'average_order_value',
        'generated_at'
    ]
    date_hierarchy = 'period_start'
    
    def formatted_total_sales(self, obj):
        return format_html(
            '<strong>${:,.2f}</strong>',
            obj.total_sales
        )
    formatted_total_sales.short_description = 'Total Sales'
    formatted_total_sales.admin_order_field = 'total_sales'
    
    def formatted_avg_order_value(self, obj):
        return format_html(
            '${:,.2f}',
            obj.average_order_value
        )
    formatted_avg_order_value.short_description = 'Avg Order Value'
    formatted_avg_order_value.admin_order_field = 'average_order_value'
    
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ProductPerformance)
class ProductPerformanceAdmin(admin.ModelAdmin):
    list_display = [
        'product',
        'period_start',
        'period_end',
        'formatted_total_sales',
        'total_orders',
        'total_items_sold',
        'formatted_avg_order_value',
        'views',
        'generated_at'
    ]
    list_filter = [
        'period_start',
        'period_end',
        'generated_at',
        'product__category',
    ]
    search_fields = [
        'product__name',
        'product__sku',
    ]
    readonly_fields = [
        'product',
        'period_start',
        'period_end',
        'total_sales',
        'total_orders',
        'total_items_sold',
        'average_order_value',
        'views',
        'generated_at'
    ]
    date_hierarchy = 'period_start'
    
    def formatted_total_sales(self, obj):
        return format_html(
            '<strong>${:,.2f}</strong>',
            obj.total_sales
        )
    formatted_total_sales.short_description = 'Total Sales'
    formatted_total_sales.admin_order_field = 'total_sales'
    
    def formatted_avg_order_value(self, obj):
        return format_html(
            '${:,.2f}',
            obj.average_order_value
        )
    formatted_avg_order_value.short_description = 'Avg Order Value'
    formatted_avg_order_value.admin_order_field = 'average_order_value'
    
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False