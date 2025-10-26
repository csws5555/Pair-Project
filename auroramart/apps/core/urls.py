from django.urls import path
from apps.core.views import AdminDashboardView
from apps.analytics.views import AnalyticsDashboardView, AnalyticsReportExportView
from .api_views import (
    CategoryPredictionView,
    ProductRecommendationsView,
    CartRecommendationsView,
    ContextualRecommendationsView
)

app_name = 'core'

urlpatterns = [
    # Admin Dashboard
    path('admin/dashboard/', AdminDashboardView.as_view(), name='admin_dashboard'),
    
    # Analytics
    path('admin/analytics/', AnalyticsDashboardView.as_view(), name='admin_analytics_dashboard'),
    path('admin/analytics/export/', AnalyticsReportExportView.as_view(), name='admin_analytics_export'),

        # Recommendation API Endpoints
    path('api/recommendations/category-prediction/', 
         CategoryPredictionView.as_view(), 
         name='category-prediction'),
    
    path('api/recommendations/product/', 
         ProductRecommendationsView.as_view(), 
         name='product-recommendations'),
    
    path('api/recommendations/cart/', 
         CartRecommendationsView.as_view(), 
         name='cart-recommendations'),
    
    path('api/recommendations/contextual/', 
         ContextualRecommendationsView.as_view(), 
         name='contextual-recommendations'),
]