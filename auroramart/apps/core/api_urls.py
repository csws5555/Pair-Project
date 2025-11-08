"""
Core API URLs
NOTE: Temporarily disabled for migration creation
"""
from django.urls import path
from .api_views import (
    CategoryPredictionView,
    ProductRecommendationsView,
    CartRecommendationsView,
    ContextualRecommendationsView
)

urlpatterns = [
    # Recommendation endpoints (fallback logic)
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