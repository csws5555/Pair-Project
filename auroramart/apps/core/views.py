from django.contrib.auth.mixins import UserPassesTestMixin
from django.views.generic import TemplateView
from django.db.models import Count, Sum, Q, F
from django.utils import timezone
from datetime import timedelta
from apps.storefront.models import Product
from apps.storefront.models import CustomerProfile
from apps.storefront.models import Order

class AdminDashboardView(UserPassesTestMixin, TemplateView):
    template_name = 'admin_panel/dashboard.html'
    
    def test_func(self):
        return self.request.user.is_staff or self.request.user.is_superuser
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Product metrics
        products = Product.objects.filter(is_active=True)
        context['total_products'] = products.count()
        context['low_stock_count'] = products.filter(
            stock__lte=F('reorder_threshold'),
            stock__gt=0
        ).count()
        context['out_of_stock_count'] = products.filter(stock=0).count()

        # Low stock alerts with color coding
        context['low_stock_products'] = products.filter(
            stock__lte=F('reorder_threshold')
        ).select_related('category').order_by('stock')[:10]
        
        # Customer metrics
        thirty_days_ago = timezone.now() - timedelta(days=30)
        context['total_customers'] = CustomerProfile.objects.filter(user__is_active=True).count()
        context['new_customers_this_month'] = CustomerProfile.objects.filter(
            user__date_joined__gte=thirty_days_ago
        ).count()
        
        # Order metrics
        orders = Order.objects.all()
        context['total_orders'] = orders.count()
        context['pending_orders'] = orders.filter(status='pending').count()
        context['total_revenue'] = orders.filter(
            status__in=['completed', 'shipped', 'delivered']
        ).aggregate(total=Sum('total_amount'))['total'] or 0
        
        # Recent activity feed
        context['recent_orders'] = Order.objects.select_related(
            'customer__user'
        ).order_by('-created_at')[:5]
        
        context['recent_products'] = Product.objects.filter(
            is_active=True
        ).order_by('-created_at')[:5]
        
        context['recent_customers'] = Customer.objects.select_related(
            'user'
        ).order_by('-user__date_joined')[:5]
        
        return context