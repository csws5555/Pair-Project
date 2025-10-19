from django.contrib import admin
from django.contrib.auth import get_user_model
from django.utils.html import format_html
from .models import CustomerProfile, CustomerNote

User = get_user_model()


class CustomerNoteInline(admin.TabularInline):
    model = CustomerNote
    fk_name = 'customer'  # This refers to the 'customer' field in CustomerNote
    extra = 1
    fields = ['admin', 'note', 'created_at']
    readonly_fields = ['created_at']
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'admin':
            kwargs['initial'] = request.user
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


# Instead of using CustomerProfile admin, we'll extend the User admin
# to include customer profile information
class CustomerProfileInline(admin.StackedInline):
    model = CustomerProfile
    can_delete = False
    verbose_name_plural = 'Customer Profile'
    fields = [
        'preferred_category', 'notes', 'customer_since',
        'order_count', 'total_spent', 'last_purchase_date'
    ]
    readonly_fields = ['customer_since']


# Custom User Admin with Customer Profile
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

class CustomerUserAdmin(BaseUserAdmin):
    """Extended User Admin for Customers"""
    list_display = [
        'username', 'email', 'first_name', 'last_name', 
        'user_type', 'is_staff', 'get_customer_tier'
    ]
    list_filter = BaseUserAdmin.list_filter + ('user_type',)
    
    inlines = [CustomerProfileInline, CustomerNoteInline]
    
    actions = ['update_customer_stats']
    
    def get_queryset(self, request):
        """Show only customer users"""
        qs = super().get_queryset(request)
        # Optionally filter to show only customers
        # return qs.filter(user_type='customer')
        return qs
    
    def get_customer_tier(self, obj):
        """Display customer tier if profile exists"""
        if hasattr(obj, 'customer_profile'):
            tier = obj.customer_profile.customer_tier
            colors = {
                'Platinum': '#E5E4E2',
                'Gold': '#FFD700',
                'Silver': '#C0C0C0',
                'Bronze': '#CD7F32'
            }
            color = colors.get(tier, '#808080')
            return format_html(
                '<span style="background-color: {}; padding: 3px 10px; '
                'border-radius: 3px; color: white; font-weight: bold;">{}</span>',
                color, tier
            )
        return '-'
    get_customer_tier.short_description = 'Customer Tier'
    
    def update_customer_stats(self, request, queryset):
        """Bulk action to update customer statistics"""
        count = 0
        for user in queryset.filter(user_type='customer'):
            if hasattr(user, 'customer_profile'):
                user.customer_profile.update_stats()
                count += 1
        self.message_user(
            request,
            f'Successfully updated statistics for {count} customer(s).'
        )
    update_customer_stats.short_description = 'Update customer statistics'


# Unregister the default User admin and register our custom one
admin.site.unregister(User)
admin.site.register(User, CustomerUserAdmin)


# Standalone CustomerProfile Admin (optional - for direct profile access)
@admin.register(CustomerProfile)
class CustomerProfileAdmin(admin.ModelAdmin):
    list_display = [
        'get_username', 'get_email', 'customer_tier_display', 
        'order_count', 'total_spent', 'last_purchase_date', 
        'customer_since'
    ]
    list_filter = [
        'customer_since', 'last_purchase_date', 
        'preferred_category'
    ]
    search_fields = [
        'user__username', 'user__email', 
        'user__first_name', 'user__last_name'
    ]
    readonly_fields = [
        'customer_since', 'get_customer_tier', 
        'get_average_order_value'
    ]
    
    fieldsets = (
        ('Customer Information', {
            'fields': ('user', 'customer_since')
        }),
        ('Preferences', {
            'fields': ('preferred_category', 'notes')
        }),
        ('Statistics', {
            'fields': (
                'order_count', 'total_spent', 'last_purchase_date',
                'get_customer_tier', 'get_average_order_value'
            ),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['update_customer_stats']
    
    def get_username(self, obj):
        return obj.user.username
    get_username.short_description = 'Username'
    get_username.admin_order_field = 'user__username'
    
    def get_email(self, obj):
        return obj.user.email
    get_email.short_description = 'Email'
    get_email.admin_order_field = 'user__email'
    
    def customer_tier_display(self, obj):
        tier = obj.customer_tier
        colors = {
            'Platinum': '#E5E4E2',
            'Gold': '#FFD700',
            'Silver': '#C0C0C0',
            'Bronze': '#CD7F32'
        }
        color = colors.get(tier, '#808080')
        return format_html(
            '<span style="background-color: {}; padding: 3px 10px; '
            'border-radius: 3px; color: white; font-weight: bold;">{}</span>',
            color, tier
        )
    customer_tier_display.short_description = 'Tier'
    
    def get_customer_tier(self, obj):
        return obj.customer_tier
    get_customer_tier.short_description = 'Customer Tier'
    
    def get_average_order_value(self, obj):
        return f"${obj.average_order_value:.2f}"
    get_average_order_value.short_description = 'Avg Order Value'
    
    def update_customer_stats(self, request, queryset):
        """Bulk action to update customer statistics"""
        count = 0
        for profile in queryset:
            profile.update_stats()
            count += 1
        self.message_user(
            request,
            f'Successfully updated statistics for {count} customer(s).'
        )
    update_customer_stats.short_description = 'Update customer statistics'


@admin.register(CustomerNote)
class CustomerNoteAdmin(admin.ModelAdmin):
    list_display = ['customer', 'admin', 'get_note_preview', 'created_at']
    list_filter = ['created_at', 'admin']
    search_fields = [
        'customer__username', 'customer__email', 
        'admin__username', 'note'
    ]
    readonly_fields = ['created_at']
    
    fieldsets = (
        ('Note Information', {
            'fields': ('customer', 'admin', 'note')
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def get_note_preview(self, obj):
        max_length = 50
        if len(obj.note) > max_length:
            return f"{obj.note[:max_length]}..."
        return obj.note
    get_note_preview.short_description = 'Note Preview'
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Filter to show only customer users for 'customer' field"""
        if db_field.name == 'customer':
            kwargs['queryset'] = User.objects.filter(user_type='customer')
        if db_field.name == 'admin':
            kwargs['initial'] = request.user
        return super().formfield_for_foreignkey(db_field, request, **kwargs)