from rest_framework import viewsets, status, filters, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q
import random

from .models import Category, Product
from .serializers import (
    CategorySerializer,
    ProductListSerializer,
    ProductDetailSerializer
)
from .filters import ProductFilter


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing categories.
    
    Provides:
    - list: Get all categories
    - retrieve: Get single category by ID
    - products: Get all products in a category (custom action)
    """
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [AllowAny]
    lookup_field = 'slug'

    def get_queryset(self):
        """
        Optionally filter to only top-level categories
        """
        queryset = Category.objects.all()
        
        # Filter for top-level categories only if requested
        top_level = self.request.query_params.get('top_level', None)
        if top_level and top_level.lower() == 'true':
            queryset = queryset.filter(parent__isnull=True)
        
        return queryset.prefetch_related('children')

    @action(detail=True, methods=['get'])
    def products(self, request, slug=None):
        """
        Get all products in this category and its subcategories.
        
        URL: /api/categories/{slug}/products/
        """
        category = self.get_object()
        
        # Get category and all its descendants
        category_ids = [category.id]
        
        # Get all subcategories recursively
        def get_subcategory_ids(cat):
            subcats = cat.children.all()
            ids = []
            for subcat in subcats:
                ids.append(subcat.id)
                ids.extend(get_subcategory_ids(subcat))
            return ids
        
        category_ids.extend(get_subcategory_ids(category))
        
        # Get products in these categories
        products = Product.objects.filter(
            category_id__in=category_ids,
            is_active=True
        ).select_related('category').prefetch_related('images')
        
        # Apply pagination
        page = self.paginate_queryset(products)
        if page is not None:
            serializer = ProductListSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)
        
        serializer = ProductListSerializer(products, many=True, context={'request': request})
        return Response(serializer.data)


class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing products.
    
    Provides:
    - list: Get all products with filtering, search, and ordering
    - retrieve: Get single product by ID or slug
    - recommendations: Get product recommendations (custom action)
    
    Filters:
    - category: Filter by category slug
    - min_price, max_price: Price range
    - min_rating: Minimum rating
    - stock_status: in_stock, low_stock, out_of_stock
    
    Search:
    - name, description
    
    Ordering:
    - price, -price
    - rating, -rating
    - created_at, -created_at
    """
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = ProductFilter
    search_fields = ['name', 'description', 'sku']
    ordering_fields = ['price', 'rating', 'created_at']
    ordering = ['-created_at']  # Default ordering
    lookup_field = 'slug'

    def get_queryset(self):
        """
        Get products with optimized queries
        """
        queryset = Product.objects.filter(is_active=True).select_related(
            'category'
        ).prefetch_related('images', 'specifications')
        
        return queryset

    def get_serializer_class(self):
        """
        Use different serializers for list vs detail views
        """
        if self.action == 'retrieve':
            return ProductDetailSerializer
        return ProductListSerializer

    @action(detail=True, methods=['get'])
    def recommendations(self, request, slug=None):
        """
        Get product recommendations (Frequently Bought Together).
        
        Phase 3: Simple fallback - random products from same category
        Phase 10: ML-based recommendations using collaborative filtering
        
        URL: /api/products/{slug}/recommendations/
        """
        product = self.get_object()
        
        # =============================================================================
        # ML INTEGRATION POINT - Phase 10
        # Current: Random products from same category (fallback)
        # TODO Phase 10: Replace with ML-based recommendations
        # - Use collaborative filtering model
        # - Consider purchase history
        # - Factor in user preferences
        # =============================================================================
        
        # Phase 3: Simple fallback logic
        recommendations = Product.objects.filter(
            category=product.category,
            is_active=True
        ).exclude(
            id=product.id
        ).select_related('category').prefetch_related('images')[:6]
        
        # If not enough products in same category, get from parent category
        if recommendations.count() < 4 and product.category.parent:
            additional = Product.objects.filter(
                category__parent=product.category.parent,
                is_active=True
            ).exclude(
                id=product.id
            ).exclude(
                id__in=[p.id for p in recommendations]
            ).select_related('category').prefetch_related('images')[:6]
            
            recommendations = list(recommendations) + list(additional)
        
        # Shuffle for variety
        recommendations = list(recommendations)
        random.shuffle(recommendations)
        recommendations = recommendations[:4]
        
        serializer = ProductListSerializer(
            recommendations,
            many=True,
            context={'request': request}
        )
        
        return Response({
            'product': product.name,
            'recommendations': serializer.data,
            'recommendation_type': 'category_based'  # Phase 10: 'ml_based'
        })

    @action(detail=False, methods=['get'])
    def featured(self, request):
        """
        Get featured products.
        
        URL: /api/products/featured/
        """
        products = self.get_queryset().filter(is_featured=True)[:12]
        serializer = ProductListSerializer(products, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def new_arrivals(self, request):
        """
        Get newest products.
        
        URL: /api/products/new-arrivals/
        """
        products = self.get_queryset().order_by('-created_at')[:12]
        serializer = ProductListSerializer(products, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def best_sellers(self, request):
        """
        Get best-selling products (by rating for now).
        
        Phase 3: Sort by rating
        Phase 10: Sort by actual sales data
        
        URL: /api/products/best-sellers/
        """
        products = self.get_queryset().order_by('-rating', '-review_count')[:12]
        serializer = ProductListSerializer(products, many=True, context={'request': request})
        return Response(serializer.data)