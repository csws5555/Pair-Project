from django.urls import path, include
from rest_framework.routers import DefaultRouter

# Import viewsets from each app
from apps.products.api_views import CategoryViewSet, ProductViewSet
from apps.cart.api_views import CartViewSet
from apps.orders.api_views import OrderViewSet, AddressViewSet
from apps.accounts.api_views import UserRegistrationView, UserProfileView
from apps.core.api_views import (
    CategoryPredictionView,
    ProductRecommendationsView,
    CartRecommendationsView,
    ContextualRecommendationsView
)
"""
Main API URL Configuration

This module routes all API endpoints for the e-commerce application.

API Structure:
- /api/products/ - Product and category endpoints
- /api/cart/ - Shopping cart management
- /api/orders/ - Order management and checkout
- /api/auth/ - User authentication and profile
"""

# Initialize DefaultRouter
router = DefaultRouter()

# Register viewsets with the router
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'products', ProductViewSet, basename='product')
router.register(r'cart', CartViewSet, basename='cart')
router.register(r'orders', OrderViewSet, basename='order')
router.register(r'addresses', AddressViewSet, basename='address')

urlpatterns = [
    # Products API (categories and products)
    path('products/', include('apps.products.urls', namespace='products')),
    
    # Cart API
    path('', include('apps.cart.urls', namespace='cart')),
    
    # Orders API (orders, checkout, addresses)
    path('', include('apps.orders.urls', namespace='orders')),
    
    # Authentication and User API
    path('auth/', include('apps.accounts.urls', namespace='accounts')),

        # Include all router-generated URLs
    path('', include(router.urls)),
    
    # Authentication endpoints
    path('accounts/register/', UserRegistrationView.as_view(), name='api_register'),
    path('accounts/profile/', UserProfileView.as_view(), name='api_profile'),
    
    # Recommendation endpoints (fallback logic, enhanced in Phase 10)
    path('recommendations/category/', 
         CategoryPredictionView.as_view(), 
         name='api_category_prediction'),
    
    path('recommendations/product/', 
         ProductRecommendationsView.as_view(), 
         name='api_product_recommendations'),
    
    path('recommendations/cart/', 
         CartRecommendationsView.as_view(), 
         name='api_cart_recommendations'),
    
    path('recommendations/contextual/', 
         ContextualRecommendationsView.as_view(), 
         name='api_contextual_recommendations'),
]