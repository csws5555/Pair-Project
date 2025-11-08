from django.contrib.auth.mixins import UserPassesTestMixin
from django.views.generic import TemplateView
from django.views import View
from django.db.models import Count, Sum, Avg, F, Q
from django.utils import timezone
from django.http import JsonResponse, HttpResponse
from datetime import timedelta, datetime
import json

class AdminRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_staff or self.request.user.is_superuser

class AnalyticsDashboardView(AdminRequiredMixin, TemplateView):
    template_name = 'admin_panel/analytics/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get time period from request
        period = self.request.GET.get('period', 'monthly')
        start_date = self.get_start_date(period)
        end_date = timezone.now()
        
        # Custom date range
        custom_start = self.request.GET.get('start_date')
        custom_end = self.request.GET.get('end_date')
        if custom_start and custom_end:
            start_date = timezone.make_aware(datetime.strptime(custom_start, '%Y-%m-%d'))
            end_date = timezone.make_aware(datetime.strptime(custom_end, '%Y-%m-%d'))
            period = 'custom'
        
        context['period'] = period
        context['start_date'] = start_date.date()
        context['end_date'] = end_date.date()
        
        from apps.storefront.models import Order, OrderItem
        from apps.storefront.models import Product, Category
        
        # Filter orders by date range
        orders = Order.objects.filter(
            created_at__gte=start_date,
            created_at__lte=end_date
        )
        
        # Key Metrics Cards
        context['total_revenue'] = orders.filter(
            status__in=['completed', 'shipped', 'delivered']
        ).aggregate(total=Sum('total_amount'))['total'] or 0
        
        context['total_orders'] = orders.count()
        context['average_order_value'] = context['total_revenue'] / context['total_orders'] if context['total_orders'] > 0 else 0
        
        context['total_customers'] = orders.values('customer').distinct().count()
        
        # Category Performance
        category_data = OrderItem.objects.filter(
            order__created_at__gte=start_date,
            order__created_at__lte=end_date,
            order__status__in=['completed', 'shipped', 'delivered']
        ).values(
            'product__category__id',
            'product__category__name'
        ).annotate(
            total_revenue=Sum(F('quantity') * F('price')),
            total_quantity=Sum('quantity'),
            order_count=Count('order', distinct=True)
        ).order_by('-total_revenue')
        
        context['category_performance'] = category_data
        
        # Prepare data for Chart.js
        context['category_chart_data'] = json.dumps({
            'labels': [item['product__category__name'] for item in category_data],
            'revenue': [float(item['total_revenue']) for item in category_data],
            'quantity': [item['total_quantity'] for item in category_data]
        })
        
        # Top Products
        top_products = OrderItem.objects.filter(
            order__created_at__gte=start_date,
            order__created_at__lte=end_date,
            order__status__in=['completed', 'shipped', 'delivered']
        ).values(
            'product__id',
            'product__name',
            'product__sku'
        ).annotate(
            total_revenue=Sum(F('quantity') * F('price')),
            total_quantity=Sum('quantity'),
            order_count=Count('order', distinct=True)
        ).order_by('-total_revenue')[:10]
        
        context['top_products'] = top_products
        
        # Trend Analysis (daily/weekly/monthly aggregation)
        trend_data = self.get_trend_data(orders, period, start_date, end_date)
        context['trend_chart_data'] = json.dumps(trend_data)
        
        # Year-over-year comparison (if applicable)
        if period == 'yearly' or (end_date - start_date).days >= 365:
            context['yoy_comparison'] = self.get_yoy_comparison(start_date, end_date)
        
        # Category Comparison Table
        context['category_comparison'] = self.get_category_comparison(start_date, end_date)
        
        return context
    
    def get_start_date(self, period):
        now = timezone.now()
        if period == 'daily':
            return now - timedelta(days=1)
        elif period == 'weekly':
            return now - timedelta(weeks=1)
        elif period == 'monthly':
            return now - timedelta(days=30)
        elif period == 'yearly':
            return now - timedelta(days=365)
        else:
            return now - timedelta(days=30)  # default
    
    def get_trend_data(self, orders, period, start_date, end_date):
        from django.db.models.functions import TruncDate, TruncWeek, TruncMonth
        
        if period == 'daily':
            trunc_func = TruncDate
            date_format = '%Y-%m-%d'
        elif period == 'weekly':
            trunc_func = TruncWeek
            date_format = '%Y-%m-%d'
        else:
            trunc_func = TruncMonth
            date_format = '%Y-%m'
        
        trend = orders.filter(
            status__in=['completed', 'shipped', 'delivered']
        ).annotate(
            period=trunc_func('created_at')
        ).values('period').annotate(
            revenue=Sum('total_amount'),
            order_count=Count('id')
        ).order_by('period')
        
        return {
            'labels': [item['period'].strftime(date_format) for item in trend],
            'revenue': [float(item['revenue']) for item in trend],
            'orders': [item['order_count'] for item in trend]
        }
    
    def get_yoy_comparison(self, start_date, end_date):
        from apps.storefront.models import Order
        
        # Current period
        current_revenue = Order.objects.filter(
            created_at__gte=start_date,
            created_at__lte=end_date,
            status__in=['completed', 'shipped', 'delivered']
        ).aggregate(total=Sum('total_amount'))['total'] or 0
        
        # Previous year same period
        prev_start = start_date - timedelta(days=365)
        prev_end = end_date - timedelta(days=365)
        
        prev_revenue = Order.objects.filter(
            created_at__gte=prev_start,
            created_at__lte=prev_end,
            status__in=['completed', 'shipped', 'delivered']
        ).aggregate(total=Sum('total_amount'))['total'] or 0
        
        if prev_revenue > 0:
            growth_rate = ((current_revenue - prev_revenue) / prev_revenue) * 100
        else:
            growth_rate = 100 if current_revenue > 0 else 0
        
        return {
            'current_revenue': current_revenue,
            'prev_revenue': prev_revenue,
            'growth_rate': growth_rate
        }
    
    def get_category_comparison(self, start_date, end_date):
        from apps.storefront.models import OrderItem
        from apps.storefront.models import Category
        
        categories = Category.objects.filter(is_active=True)
        comparison_data = []
        
        for category in categories:
            current_data = OrderItem.objects.filter(
                order__created_at__gte=start_date,
                order__created_at__lte=end_date,
                order__status__in=['completed', 'shipped', 'delivered'],
                product__category=category
            ).aggregate(
                revenue=Sum(F('quantity') * F('price')),
                quantity=Sum('quantity'),
                orders=Count('order', distinct=True)
            )
            
            # Previous period (same duration)
            duration = (end_date - start_date).days
            prev_start = start_date - timedelta(days=duration)
            prev_end = start_date
            
            prev_data = OrderItem.objects.filter(
                order__created_at__gte=prev_start,
                order__created_at__lte=prev_end,
                order__status__in=['completed', 'shipped', 'delivered'],
                product__category=category
            ).aggregate(
                revenue=Sum(F('quantity') * F('price')),
                quantity=Sum('quantity')
            )
            
            current_revenue = current_data['revenue'] or 0
            prev_revenue = prev_data['revenue'] or 0
            
            if prev_revenue > 0:
                growth = ((current_revenue - prev_revenue) / prev_revenue) * 100
            else:
                growth = 100 if current_revenue > 0 else 0
            
            comparison_data.append({
                'category': category,
                'current_revenue': current_revenue,
                'quantity': current_data['quantity'] or 0,
                'orders': current_data['orders'] or 0,
                'growth': growth
            })
        
        return sorted(comparison_data, key=lambda x: x['current_revenue'], reverse=True)

class AnalyticsReportExportView(AdminRequiredMixin, View):
    def get(self, request):
        period = request.GET.get('period', 'monthly')
        format_type = request.GET.get('format', 'csv')
        
        start_date = self.get_start_date(period)
        end_date = timezone.now()
        
        custom_start = request.GET.get('start_date')
        custom_end = request.GET.get('end_date')
        if custom_start and custom_end:
            start_date = timezone.make_aware(datetime.strptime(custom_start, '%Y-%m-%d'))
            end_date = timezone.make_aware(datetime.strptime(custom_end, '%Y-%m-%d'))
        
        if format_type == 'csv':
            return self.export_csv(start_date, end_date)
        else:
            messages.error(request, 'Invalid export format')
            return redirect('admin_analytics_dashboard')
    
    def get_start_date(self, period):
        now = timezone.now()
        if period == 'daily':
            return now - timedelta(days=1)
        elif period == 'weekly':
            return now - timedelta(weeks=1)
        elif period == 'monthly':
            return now - timedelta(days=30)
        elif period == 'yearly':
            return now - timedelta(days=365)
        else:
            return now - timedelta(days=30)
    
    def export_csv(self, start_date, end_date):
        from apps.storefront.models import OrderItem
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="analytics_report_{start_date.date()}_to_{end_date.date()}.csv"'
        
        writer = csv.writer(response)
        
        # Summary Section
        writer.writerow(['Analytics Report'])
        writer.writerow(['Period', f'{start_date.date()} to {end_date.date()}'])
        writer.writerow([])
        
        # Category Performance
        writer.writerow(['Category Performance'])
        writer.writerow(['Category', 'Revenue', 'Quantity Sold', 'Number of Orders', 'Avg Order Value'])
        
        category_data = OrderItem.objects.filter(
            order__created_at__gte=start_date,
            order__created_at__lte=end_date,
            order__status__in=['completed', 'shipped', 'delivered']
        ).values(
            'product__category__name'
        ).annotate(
            total_revenue=Sum(F('quantity') * F('price')),
            total_quantity=Sum('quantity'),
            order_count=Count('order', distinct=True)
        ).order_by('-total_revenue')
        
        for item in category_data:
            avg_order = item['total_revenue'] / item['order_count'] if item['order_count'] > 0 else 0
            writer.writerow([
                item['product__category__name'],
                f"{item['total_revenue']:.2f}",
                item['total_quantity'],
                item['order_count'],
                f"{avg_order:.2f}"
            ])
        
        writer.writerow([])
        
        # Top Products
        writer.writerow(['Top 20 Products'])
        writer.writerow(['Product Name', 'SKU', 'Revenue', 'Quantity Sold', 'Number of Orders'])
        
        top_products = OrderItem.objects.filter(
            order__created_at__gte=start_date,
            order__created_at__lte=end_date,
            order__status__in=['completed', 'shipped', 'delivered']
        ).values(
            'product__name',
            'product__sku'
        ).annotate(
            total_revenue=Sum(F('quantity') * F('price')),
            total_quantity=Sum('quantity'),
            order_count=Count('order', distinct=True)
        ).order_by('-total_revenue')[:20]
        
        for item in top_products:
            writer.writerow([
                item['product__name'],
                item['product__sku'],
                f"{item['total_revenue']:.2f}",
                item['total_quantity'],
                item['order_count']
            ])
        
        return response
