from django.urls import path
from apps.core.views import AdminDashboardView
from apps.analytics.views import AnalyticsDashboardView, AnalyticsReportExportView

app_name = 'core'

urlpatterns = [
    # Admin Dashboard
    path('admin/dashboard/', AdminDashboardView.as_view(), name='admin_dashboard'),
    
    # Analytics
    path('admin/analytics/', AnalyticsDashboardView.as_view(), name='admin_analytics_dashboard'),
    path('admin/analytics/export/', AnalyticsReportExportView.as_view(), name='admin_analytics_export'),
]