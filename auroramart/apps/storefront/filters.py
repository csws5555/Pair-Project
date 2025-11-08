"""
Product filters using django-filter
"""
import django_filters
from .models import Product, Category


class ProductFilter(django_filters.FilterSet):
    """Filter for product listing pages"""

    # Price range filter
    min_price = django_filters.NumberFilter(field_name='price', lookup_expr='gte', label='Min Price')
    max_price = django_filters.NumberFilter(field_name='price', lookup_expr='lte', label='Max Price')

    # Category filter
    category = django_filters.ModelChoiceFilter(
        queryset=Category.objects.filter(is_active=True),
        label='Category'
    )

    # Stock availability filter
    in_stock = django_filters.BooleanFilter(
        method='filter_in_stock',
        label='In Stock Only'
    )

    # Rating filter
    min_rating = django_filters.NumberFilter(field_name='rating', lookup_expr='gte', label='Min Rating')

    # =============================================================================
    # ML INTEGRATION POINT - Phase 10
    # Current: Basic filtering
    # TODO Phase 10: Add ML-powered filters (recommended for you, trending, etc.)
    # =============================================================================

    class Meta:
        model = Product
        fields = ['category', 'in_stock']

    def filter_in_stock(self, queryset, name, value):
        """Filter products that are in stock"""
        if value:
            return queryset.filter(stock__gt=0)
        return queryset
