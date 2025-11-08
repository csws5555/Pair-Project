from django.contrib.auth.mixins import UserPassesTestMixin, LoginRequiredMixin
from django.views.generic import ListView, DetailView, UpdateView, CreateView, DeleteView, TemplateView
from django.urls import reverse_lazy
from django.db.models import Q, Sum, Count, F
from django.contrib import messages
from django.shortcuts import redirect, get_object_or_404
from django.views import View
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

from apps.storefront.models import Product
from apps.storefront.models import Order
from .models import CustomerProfile

User = get_user_model()

class AdminRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Mixin to require admin/staff access"""
    def test_func(self):
        return self.request.user.is_staff or self.request.user.is_superuser


class AdminDashboardView(AdminRequiredMixin, TemplateView):
    """Main admin dashboard with statistics"""
    template_name = 'customers/admin_dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Calculate statistics
        today = timezone.now()
        last_30_days = today - timedelta(days=30)

        # Order statistics
        context['total_orders'] = Order.objects.count()
        context['orders_this_month'] = Order.objects.filter(
            created_at__gte=last_30_days
        ).count()

        # Revenue statistics
        revenue_stats = Order.objects.filter(
            status__in=['processing', 'shipped', 'delivered']
        ).aggregate(
            total_revenue=Sum('total'),
            monthly_revenue=Sum('total', filter=Q(created_at__gte=last_30_days))
        )
        context['total_revenue'] = revenue_stats['total_revenue'] or 0
        context['monthly_revenue'] = revenue_stats['monthly_revenue'] or 0

        # Customer statistics
        context['total_customers'] = User.objects.filter(is_active=True).count()
        context['new_customers_this_month'] = User.objects.filter(
            date_joined__gte=last_30_days
        ).count()

        # Product statistics
        context['total_products'] = Product.objects.filter(is_active=True).count()
        context['low_stock_products'] = Product.objects.filter(
            stock__lte=F('reorder_threshold'),
            is_active=True
        ).count()

        # Recent orders
        context['recent_orders'] = Order.objects.select_related('user').order_by('-created_at')[:10]

        return context


class CustomerListView(AdminRequiredMixin, ListView):
    """List all customers"""
    model = User
    template_name = 'customers/customer_list.html'
    context_object_name = 'customers'
    paginate_by = 20

    def get_queryset(self):
        queryset = User.objects.filter(is_active=True).order_by('-date_joined')

        # Search functionality
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(username__icontains=search) |
                Q(email__icontains=search) |
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search)
            )

        return queryset


class CustomerDetailView(AdminRequiredMixin, DetailView):
    """View customer details"""
    model = User
    template_name = 'customers/customer_detail.html'
    context_object_name = 'customer'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        customer = self.get_object()

        # Get or create customer profile
        profile, created = CustomerProfile.objects.get_or_create(user=customer)
        if created or profile.order_count == 0:
            profile.update_stats()

        context['profile'] = profile
        context['orders'] = Order.objects.filter(user=customer).order_by('-created_at')[:10]
        context['total_orders'] = Order.objects.filter(user=customer).count()

        return context


class CustomerUpdateView(AdminRequiredMixin, UpdateView):
    """Update customer information"""
    model = User
    template_name = 'customers/customer_form.html'
    fields = ['username', 'email', 'first_name', 'last_name', 'is_active']

    def get_success_url(self):
        messages.success(self.request, 'Customer updated successfully.')
        return reverse_lazy('admin_panel:customer_detail', kwargs={'pk': self.object.pk})


class AdminOrderListView(AdminRequiredMixin, ListView):
    """List all orders"""
    model = Order
    template_name = 'customers/order_list.html'
    context_object_name = 'orders'
    paginate_by = 20

    def get_queryset(self):
        queryset = Order.objects.select_related('user').order_by('-created_at')

        # Filter by status
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)

        # Search by order number or customer
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(order_number__icontains=search) |
                Q(user__username__icontains=search) |
                Q(user__email__icontains=search)
            )

        return queryset


class AdminOrderDetailView(AdminRequiredMixin, DetailView):
    """View order details"""
    model = Order
    template_name = 'customers/order_detail.html'
    context_object_name = 'order'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        order = self.get_object()
        context['items'] = order.items.select_related('product').all()
        return context


class OrderStatusUpdateView(AdminRequiredMixin, UpdateView):
    """Update order status"""
    model = Order
    template_name = 'customers/order_status_form.html'
    fields = ['status']

    def get_success_url(self):
        messages.success(self.request, 'Order status updated successfully.')
        return reverse_lazy('admin_panel:order_detail', kwargs={'pk': self.object.pk})


class AdminProductListView(AdminRequiredMixin, ListView):
    """List all products for admin"""
    model = Product
    template_name = 'customers/product_list.html'
    context_object_name = 'products'
    paginate_by = 20

    def get_queryset(self):
        queryset = Product.objects.select_related('category').order_by('-created_at')

        # Search functionality
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(sku__icontains=search) |
                Q(description__icontains=search)
            )

        # Filter by category
        category = self.request.GET.get('category')
        if category:
            queryset = queryset.filter(category_id=category)

        # Filter by stock status
        stock_filter = self.request.GET.get('stock')
        if stock_filter == 'low':
            queryset = queryset.filter(stock__lte=F('reorder_threshold'))
        elif stock_filter == 'out':
            queryset = queryset.filter(stock=0)

        return queryset


class AdminProductCreateView(AdminRequiredMixin, CreateView):
    """Create new product"""
    model = Product
    template_name = 'customers/product_form.html'
    fields = ['sku', 'name', 'description', 'category', 'price', 'original_price',
              'stock', 'reorder_threshold', 'is_active', 'is_featured']

    def get_success_url(self):
        messages.success(self.request, 'Product created successfully.')
        return reverse_lazy('admin_panel:product_list')


class AdminProductUpdateView(AdminRequiredMixin, UpdateView):
    """Update product"""
    model = Product
    template_name = 'customers/product_form.html'
    fields = ['name', 'description', 'category', 'price', 'original_price',
              'stock', 'reorder_threshold', 'is_active', 'is_featured']

    def get_success_url(self):
        messages.success(self.request, 'Product updated successfully.')
        return reverse_lazy('admin_panel:product_list')


class AdminProductDeleteView(AdminRequiredMixin, DeleteView):
    """Delete product"""
    model = Product
    template_name = 'customers/product_confirm_delete.html'
    success_url = reverse_lazy('admin_panel:product_list')

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, 'Product deleted successfully.')
        return super().delete(request, *args, **kwargs)


class CustomerToggleStatusView(AdminRequiredMixin, View):
    """Toggle customer active status"""
    def post(self, request, pk):
        customer = get_object_or_404(User, pk=pk)
        customer.is_active = not customer.is_active
        customer.save()

        status = 'activated' if customer.is_active else 'deactivated'
        messages.success(request, f'Customer account {status} successfully.')

        return redirect('admin_panel:customer_detail', pk=pk)