"""
Recommendations App URL Configuration
API endpoints for ML-powered recommendations
"""
from django.urls import path
from . import views

app_name = 'api'

urlpatterns = [
    # Recommendation endpoints
    path('recommendations/products/', views.ProductRecommendationView.as_view(), name='product_recommendations'),
    path('recommendations/category/', views.CategoryRecommendationView.as_view(), name='category_recommendation'),
    path('recommendations/personalized/', views.PersonalizedRecommendationView.as_view(), name='personalized_recommendations'),
    
    # Prediction endpoints
    path('predict/category/', views.CategoryPredictionView.as_view(), name='category_prediction'),
    path('predict/purchase/', views.PurchasePredictionView.as_view(), name='purchase_prediction'),
    
    # Tracking endpoints (for ML data collection)
    path('track/view/', views.TrackProductViewView.as_view(), name='track_view'),
    path('track/click/', views.TrackClickView.as_view(), name='track_click'),
]