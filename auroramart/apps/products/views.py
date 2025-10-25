from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView
from django.db.models import Q, Prefetch, Count, Avg, F
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.core.paginator import Paginator
from django.contrib import messages
from .models import Product, Category, ProductImage, BrowsingHistory
from .filters import ProductFilter
from apps.core.recommendation_utils import (
    get_category_prediction,
    get_frequently_bought_together,
    get_contextual_recommendations
)
import random


class HomeView(ListView):
    """Homepage view with featured products and personalized content"""
    model = Product
    template_name = 'products/home.html'
    context_object_name = 'products'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Featured products (products marked as featured)
        context['featured_products'] = Product.objects.filter(
            is_active=True,
            is_featured=True
        ).select_related('category').prefetch_related('images')[:8]
        
        # New arrivals (most recent products)
        context['new_arrivals'] = Product.objects.filter(
            is_active=True
        ).select_related('category').prefetch_related('images').order_by('-created_at')[:8]
        
        # Top rated products
        context['top_rated'] = Product.objects.filter(
            is_active=True
        ).annotate(
            avg_rating=Avg('reviews__rating')
        ).filter(avg_rating__gte=4.0).select_related('category').prefetch_related('images')[:8]
        
        # Category quick links
        context['categories'] = Category.objects.filter(
            parent=None,
            is_active=True
        ).prefetch_related('children')[:8]
        
        # Personalized content for logged-in users
        if self.request.user.is_authenticated:
            context['show_personalization'] = True
            # Get user's predicted category from profile
            if hasattr(self.request.user, 'predicted_category') and self.request.user.predicted_category:
                context['recommended_category'] = self.request.user.predicted_category
                context['recommended_products'] = Product.objects.filter(
                    category=self.request.user.predicted_category,
                    is_active=True
                ).select_related('category').prefetch_related('images')[:4]
        
        return context


class PersonalizedCategoryView(ListView):
    """Personalized category landing page based on user profile (OS-001)"""
    model = Product
    template_name = 'products/personalized_category.html'
    context_object_name = 'products'
    paginate_by = 20
    
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def get_queryset(self):
        # Get user's predicted category
        predicted_category = None
        if hasattr(self.request.user, 'predicted_category'):
            predicted_category = self.request.user.predicted_category
        
        if not predicted_category:
            # Fallback: use most popular category or random
            predicted_category = Category.objects.annotate(
                product_count=Count('products')
            ).order_by('-product_count').first()
        
        self.category = predicted_category
        
        queryset = Product.objects.filter(
            category=predicted_category,
            is_active=True
        ).select_related('category').prefetch_related('images')
        
        # Apply filters
        self.filterset = ProductFilter(self.request.GET, queryset=queryset)
        queryset = self.filterset.qs
        
        # Apply sorting
        sort_by = self.request.GET.get('sort', '-created_at')
        valid_sorts = ['price', '-price', 'name', '-name', '-created_at', 'rating']
        if sort_by in valid_sorts:
            if sort_by == 'rating':
                queryset = queryset.annotate(avg_rating=Avg('reviews__rating')).order_by('-avg_rating')
            else:
                queryset = queryset.order_by(sort_by)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['category'] = self.category
        context['filterset'] = self.filterset
        context['current_sort'] = self.request.GET.get('sort', '-created_at')
        
        # Subcategories
        context['subcategories'] = Category.objects.filter(
            parent=self.category,
            is_active=True
        )
        
        return context


class CategoryBrowseView(ListView):
    """Browse products by category with filters and recommendations (OS-005, OS-006)"""
    model = Product
    template_name = 'products/category_browse.html'
    context_object_name = 'products'
    paginate_by = 20
    
    def get_queryset(self):
        self.category = get_object_or_404(
            Category,
            slug=self.kwargs['slug'],
            is_active=True
        )
        
        # Get products from this category and its subcategories
        categories = [self.category]
        # Get all child categories recursively
        def get_children(cat):
            children = list(Category.objects.filter(parent=cat, is_active=True))
            for child in children:
                children.extend(get_children(child))
            return children
        categories.extend(get_children(self.category))

        queryset = Product.objects.filter(
            category__in=categories,
            is_active=True
        ).select_related('category').prefetch_related('images')
        
        # Apply filters using django-filter
        self.filterset = ProductFilter(self.request.GET, queryset=queryset)
        queryset = self.filterset.qs
        
        # Apply sorting
        sort_by = self.request.GET.get('sort', '-created_at')
        valid_sorts = ['price', '-price', 'name', '-name', '-created_at', 'rating']
        if sort_by in valid_sorts:
            if sort_by == 'rating':
                queryset = queryset.annotate(avg_rating=Avg('reviews__rating')).order_by('-avg_rating')
            else:
                queryset = queryset.order_by(sort_by)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['category'] = self.category
        context['filterset'] = self.filterset
        context['current_sort'] = self.request.GET.get('sort', '-created_at')
        
        # Breadcrumb navigation
        context['breadcrumbs'] = self.category.get_ancestors(include_self=True)
        
        # Subcategories
        context['subcategories'] = Category.objects.filter(
            parent=self.category,
            is_active=True
        )
        
        # =============================================================================
        # ML INTEGRATION POINT - Phase 10
        # Current: Using fallback contextual recommendations
        # TODO Phase 10: Use ML contextual recommendations
        # =============================================================================
        if self.request.user.is_authenticated:
            # Get viewed products from session
            viewed_products = self.request.session.get('viewed_products', [])
            context['recommended_products'] = get_contextual_recommendations(viewed_products)

        return context


class ProductDetailView(DetailView):
    """Product detail page with related products and tracking (OS-010)"""
    model = Product
    template_name = 'products/product_detail.html'
    context_object_name = 'product'
    slug_field = 'slug'
    
    def get_queryset(self):
        return Product.objects.filter(
            is_active=True
        ).select_related('category').prefetch_related(
            'images',
            'specifications',
            'reviews'
        )
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        product = self.object
        
        # Product images
        context['images'] = product.images.all()
        
        # Average rating and review count
        reviews = product.reviews.all()
        context['review_count'] = reviews.count()
        context['average_rating'] = reviews.aggregate(Avg('rating'))['rating__avg'] or 0
        
        # Stock status
        context['in_stock'] = product.stock > 0
        context['low_stock'] = 0 < product.stock <= 10
        
        # Specifications
        context['specifications'] = product.specifications.all()
        
        # Breadcrumb navigation (placeholder - needs proper implementation)
        # context['breadcrumbs'] = product.category.get_ancestors(include_self=True)

        # =============================================================================
        # ML INTEGRATION POINT - Phase 10
        # Current: Using fallback FBT recommendations
        # TODO Phase 10: Use ML association rules for FBT
        # =============================================================================
        context['frequently_bought_together'] = get_frequently_bought_together(product)

        # Related products (same category)
        context['related_products'] = Product.objects.filter(
            category=product.category,
            is_active=True
        ).exclude(id=product.id).select_related('category').prefetch_related('images')[:8]

        # Track browsing history
        if self.request.user.is_authenticated:
            BrowsingHistory.objects.create(
                user=self.request.user,
                product=product
            )

        # Track in session for contextual recommendations
        viewed_products = self.request.session.get('viewed_products', [])
        if product.id not in viewed_products:
            viewed_products.append(product.id)
            viewed_products = viewed_products[-50:]  # Keep last 50
            self.request.session['viewed_products'] = viewed_products

        return context


class ProductSearchView(ListView):
    """Product search view with filters (OS-002)"""
    model = Product
    template_name = 'products/product_search.html'
    context_object_name = 'products'
    paginate_by = 20
    
    def get_queryset(self):
        query = self.request.GET.get('q', '').strip()
        self.search_query = query
        
        if not query:
            return Product.objects.none()
        
        # Full-text search across name and description
        queryset = Product.objects.filter(
            Q(name__icontains=query) | Q(description__icontains=query),
            is_active=True
        ).select_related('category').prefetch_related('images')
        
        # Apply filters
        self.filterset = ProductFilter(self.request.GET, queryset=queryset)
        queryset = self.filterset.qs
        
        # Apply sorting
        sort_by = self.request.GET.get('sort', '-created_at')
        valid_sorts = ['price', '-price', 'name', '-name', '-created_at', 'rating']
        if sort_by in valid_sorts:
            if sort_by == 'rating':
                queryset = queryset.annotate(avg_rating=Avg('reviews__rating')).order_by('-avg_rating')
            else:
                queryset = queryset.order_by(sort_by)
        
        # Track search query for analytics
        self._track_search_query(query, queryset.count())
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.search_query
        context['result_count'] = self.get_queryset().count()
        context['filterset'] = self.filterset
        context['current_sort'] = self.request.GET.get('sort', '-created_at')
        return context
    
    def _track_search_query(self, query, result_count):
        """Track search queries for analytics"""
        # TODO: Implement search analytics tracking
        # This could be saved to a SearchQuery model for analysis
        pass

from django.contrib.auth.mixins import UserPassesTestMixin
from django.views.generic import CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib import messages
from django.views import View
from .models import Product, ProductImage, ProductSpecification
from .forms import ProductForm, ProductImageFormSet, ProductSpecificationFormSet
from django import forms as django_forms

class AdminRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_staff or self.request.user.is_superuser
    
    def handle_no_permission(self):
        messages.error(self.request, "You don't have permission to access this page.")
        return redirect('home')

class ProductListView(AdminRequiredMixin, ListView):
    model = Product
    template_name = 'admin_panel/products/product_list.html'
    context_object_name = 'products'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Product.objects.select_related('category').prefetch_related('images')
        
        # Search
        search_query = self.request.GET.get('search', '')
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query) |
                Q(sku__icontains=search_query) |
                Q(description__icontains=search_query)
            )
        
        # Filter by category
        category_id = self.request.GET.get('category', '')
        if category_id:
            queryset = queryset.filter(category_id=category_id)
        
        # Filter by status
        status = self.request.GET.get('status', '')
        if status == 'active':
            queryset = queryset.filter(is_active=True)
        elif status == 'inactive':
            queryset = queryset.filter(is_active=False)
        
        # Filter by stock status
        stock_status = self.request.GET.get('stock_status', '')
        if stock_status == 'low':
            queryset = queryset.filter(
                stock__lte=F('reorder_threshold'),
                stock__gt=0
            )
        elif stock_status == 'out':
            queryset = queryset.filter(stock=0)
        
        # Sort
        sort_by = self.request.GET.get('sort', '-created_at')
        queryset = queryset.order_by(sort_by)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from apps.products.models import Category
        context['categories'] = Category.objects.filter(is_active=True)
        context['search_query'] = self.request.GET.get('search', '')
        context['current_category'] = self.request.GET.get('category', '')
        context['current_status'] = self.request.GET.get('status', '')
        context['current_stock_status'] = self.request.GET.get('stock_status', '')
        context['current_sort'] = self.request.GET.get('sort', '-created_at')
        return context

class ProductCreateView(AdminRequiredMixin, CreateView):
    model = Product
    form_class = ProductForm
    template_name = 'admin_panel/products/product_form.html'
    success_url = reverse_lazy('admin_product_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['image_formset'] = ProductImageFormSet(self.request.POST, self.request.FILES)
            context['spec_formset'] = ProductSpecificationFormSet(self.request.POST)
        else:
            context['image_formset'] = ProductImageFormSet()
            context['spec_formset'] = ProductSpecificationFormSet()
        return context
    
    def form_valid(self, form):
        context = self.get_context_data()
        image_formset = context['image_formset']
        spec_formset = context['spec_formset']
        
        if image_formset.is_valid() and spec_formset.is_valid():
            self.object = form.save()
            
            image_formset.instance = self.object
            image_formset.save()
            
            spec_formset.instance = self.object
            spec_formset.save()
            
            messages.success(self.request, f'Product "{self.object.name}" created successfully.')
            return redirect(self.success_url)
        else:
            return self.form_invalid(form)

class ProductUpdateView(AdminRequiredMixin, UpdateView):
    model = Product
    form_class = ProductForm
    template_name = 'admin_panel/products/product_form.html'
    success_url = reverse_lazy('admin_product_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['image_formset'] = ProductImageFormSet(
                self.request.POST, 
                self.request.FILES, 
                instance=self.object
            )
            context['spec_formset'] = ProductSpecificationFormSet(
                self.request.POST, 
                instance=self.object
            )
        else:
            context['image_formset'] = ProductImageFormSet(instance=self.object)
            context['spec_formset'] = ProductSpecificationFormSet(instance=self.object)
        return context
    
    def form_valid(self, form):
        context = self.get_context_data()
        image_formset = context['image_formset']
        spec_formset = context['spec_formset']
        
        if image_formset.is_valid() and spec_formset.is_valid():
            self.object = form.save()
            image_formset.save()
            spec_formset.save()
            
            messages.success(self.request, f'Product "{self.object.name}" updated successfully.')
            return redirect(self.success_url)
        else:
            return self.form_invalid(form)

class ProductDeleteView(AdminRequiredMixin, DeleteView):
    model = Product
    template_name = 'admin_panel/products/product_confirm_delete.html'
    success_url = reverse_lazy('admin_product_list')
    
    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        # Soft delete
        self.object.is_active = False
        self.object.save()
        messages.success(request, f'Product "{self.object.name}" deleted successfully.')
        return redirect(self.success_url)

class ProductBulkActionView(AdminRequiredMixin, View):
    def post(self, request):
        action = request.POST.get('action')
        product_ids = request.POST.getlist('product_ids')
        
        if not product_ids:
            messages.error(request, 'No products selected.')
            return redirect('admin_product_list')
        
        products = Product.objects.filter(id__in=product_ids)
        
        if action == 'delete':
            count = products.update(is_active=False)
            messages.success(request, f'{count} products deleted successfully.')
        elif action == 'activate':
            count = products.update(is_active=True)
            messages.success(request, f'{count} products activated successfully.')
        elif action == 'deactivate':
            count = products.update(is_active=False)
            messages.success(request, f'{count} products deactivated successfully.')
        else:
            messages.error(request, 'Invalid action.')
        
        return redirect('admin_product_list')
    
import csv
from django.http import HttpResponse
from django.views.generic import FormView
from decimal import Decimal, InvalidOperation
from .forms import ProductImportForm

class ProductExportView(AdminRequiredMixin, View):
    def get(self, request):
        # Get filter parameters
        category_id = request.GET.get('category', '')
        status = request.GET.get('status', '')
        
        queryset = Product.objects.select_related('category')
        
        if category_id:
            queryset = queryset.filter(category_id=category_id)
        if status == 'active':
            queryset = queryset.filter(is_active=True)
        elif status == 'inactive':
            queryset = queryset.filter(is_active=False)
        
        # Create CSV response
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="products_export.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'SKU', 'Name', 'Category', 'Description', 'Price',
            'Stock', 'Reorder Threshold', 'Is Active', 'Is Featured'
        ])

        for product in queryset:
            writer.writerow([
                product.sku,
                product.name,
                product.category.name if product.category else '',
                product.description,
                product.price,
                product.stock,
                product.reorder_threshold,
                product.is_active,
                product.is_featured,
            ])
        
        return response

class ProductImportView(AdminRequiredMixin, FormView):
    template_name = 'admin_panel/products/product_import.html'
    form_class = ProductImportForm
    success_url = reverse_lazy('admin_product_list')
    
    def form_valid(self, form):
        csv_file = form.cleaned_data['csv_file']
        
        # Read and decode CSV
        decoded_file = csv_file.read().decode('utf-8').splitlines()
        reader = csv.DictReader(decoded_file)
        
        preview_data = []
        errors = []
        valid_rows = []
        
        from apps.products.models import Category
        
        for line_num, row in enumerate(reader, start=2):
            row_data = {
                'line': line_num,
                'data': row,
                'errors': [],
                'status': 'valid'
            }
            
            # Validate required fields
            if not row.get('SKU'):
                row_data['errors'].append('SKU is required')
            if not row.get('Name'):
                row_data['errors'].append('Name is required')
            if not row.get('Category'):
                row_data['errors'].append('Category is required')
            
            # Validate price
            try:
                price = Decimal(row.get('Price', 0))
                if price < 0:
                    row_data['errors'].append('Price cannot be negative')
            except (InvalidOperation, ValueError):
                row_data['errors'].append('Invalid price format')
            
            # Validate stock quantity
            try:
                stock = int(row.get('Stock Quantity', 0))
                if stock < 0:
                    row_data['errors'].append('Stock quantity cannot be negative')
            except ValueError:
                row_data['errors'].append('Invalid stock quantity format')
            
            # Validate category exists
            category_name = row.get('Category')
            if category_name:
                if not Category.objects.filter(name=category_name).exists():
                    row_data['errors'].append(f'Category "{category_name}" does not exist')
            
            if row_data['errors']:
                row_data['status'] = 'error'
                errors.append(row_data)
            else:
                valid_rows.append(row)
            
            preview_data.append(row_data)
        
        # Store in session for confirmation
        self.request.session['import_preview'] = preview_data
        self.request.session['import_valid_rows'] = valid_rows
        
        return self.render_to_response(
            self.get_context_data(
                form=form,
                preview_data=preview_data,
                total_rows=len(preview_data),
                valid_rows=len(valid_rows),
                error_rows=len(errors),
                show_preview=True
            )
        )

class ProductImportConfirmView(AdminRequiredMixin, View):
    def post(self, request):
        valid_rows = request.session.get('import_valid_rows', [])
        
        if not valid_rows:
            messages.error(request, 'No valid data to import.')
            return redirect('admin_product_import')
        
        from apps.products.models import Category
        
        created_count = 0
        updated_count = 0
        
        for row in valid_rows:
            category = Category.objects.get(name=row['Category'])
            
            product, created = Product.objects.update_or_create(
                sku=row['SKU'],
                defaults={
                    'name': row['Name'],
                    'category': category,
                    'description': row.get('Description', ''),
                    'price': Decimal(row.get('Price', 0)),
                    'stock': int(row.get('Stock', 0)),
                    'reorder_threshold': int(row.get('Reorder Threshold', 0)),
                    'is_active': row.get('Is Active', 'True').lower() == 'true',
                    'is_featured': row.get('Is Featured', 'False').lower() == 'true',
                }
            )
            
            if created:
                created_count += 1
            else:
                updated_count += 1
        
        # Clear session data
        del request.session['import_preview']
        del request.session['import_valid_rows']
        
        messages.success(
            request,
            f'Import completed: {created_count} products created, {updated_count} products updated.'
        )
        return redirect('admin_product_list')
    
class InventoryDashboardView(AdminRequiredMixin, ListView):
    model = Product
    template_name = 'admin_panel/inventory/inventory_dashboard.html'
    context_object_name = 'products'
    paginate_by = 50
    
    def get_queryset(self):
        queryset = Product.objects.select_related('category').filter(is_active=True)
        
        # Filter by stock status
        stock_status = self.request.GET.get('stock_status', '')
        if stock_status == 'adequate':
            queryset = queryset.filter(stock__gt=F('reorder_threshold'))
        elif stock_status == 'low':
            queryset = queryset.filter(
                stock__lte=F('reorder_threshold'),
                stock__gt=0
            )
        elif stock_status == 'out':
            queryset = queryset.filter(stock=0)
        
        # Filter by category
        category_id = self.request.GET.get('category', '')
        if category_id:
            queryset = queryset.filter(category_id=category_id)
        
        return queryset.order_by('stock')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from apps.products.models import Category
        
        context['categories'] = Category.objects.filter(is_active=True)
        context['current_stock_status'] = self.request.GET.get('stock_status', '')
        context['current_category'] = self.request.GET.get('category', '')
        
        # Summary statistics
        all_products = Product.objects.filter(is_active=True)
        context['adequate_stock'] = all_products.filter(
            stock__gt=F('reorder_threshold')
        ).count()
        context['low_stock'] = all_products.filter(
            stock__lte=F('reorder_threshold'),
            stock__gt=0
        ).count()
        context['out_of_stock'] = all_products.filter(stock=0).count()
        
        return context

class StockAdjustmentView(AdminRequiredMixin, View):
    def post(self, request, pk):
        product = Product.objects.get(pk=pk)
        adjustment_type = request.POST.get('adjustment_type')
        quantity = int(request.POST.get('quantity', 0))
        reason = request.POST.get('reason', '')
        
        if adjustment_type == 'add':
            product.stock += quantity
        elif adjustment_type == 'subtract':
            product.stock = max(0, product.stock - quantity)
        elif adjustment_type == 'set':
            product.stock = quantity
        
        product.save()
        
        # Log the adjustment (you can create a StockAdjustment model for this)
        messages.success(
            request,
            f'Stock adjusted for "{product.name}". New quantity: {product.stock}'
        )
        
        return redirect('admin_inventory_dashboard')

class ReorderThresholdUpdateView(AdminRequiredMixin, View):
    def post(self, request, pk):
        product = Product.objects.get(pk=pk)
        new_threshold = int(request.POST.get('reorder_threshold', 0))
        
        product.reorder_threshold = new_threshold
        product.save()
        
        messages.success(
            request,
            f'Reorder threshold updated for "{product.name}" to {new_threshold}'
        )
        
        return redirect('admin_inventory_dashboard')

class InventoryReportView(AdminRequiredMixin, View):
    def get(self, request):
        products = Product.objects.select_related('category').filter(is_active=True)
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="inventory_report.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'SKU', 'Product Name', 'Category', 'Stock Quantity',
            'Reorder Threshold', 'Stock Status', 'Value (Price × Quantity)'
        ])
        
        for product in products:
            if product.stock > product.reorder_threshold:
                stock_status = 'Adequate'
            elif product.stock > 0:
                stock_status = 'Low Stock'
            else:
                stock_status = 'Out of Stock'
            
            value = product.price * product.stock
            
            writer.writerow([
                product.sku,
                product.name,
                product.category.name if product.category else '',
                product.stock,
                product.reorder_threshold,
                stock_status,
                f'{value:.2f}',
            ])
        
        return response