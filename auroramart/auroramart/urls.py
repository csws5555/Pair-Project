"""
URL configuration for auroramart project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api-auth/', include('rest_framework.urls')),

    # =============================================================================
    # ML INTEGRATION POINT - Phase 10
    # Current: Recommendations URL commented out
    # TODO Phase 10: Uncomment recommendations URL and implement ML endpoints
    # =============================================================================
    path('admin-panel/', include('apps.customers.urls', namespace='admin_panel')),
    path('admin-panel/analytics/', include('apps.analytics.urls', namespace='analytics')),
    path('api/products/', include('apps.products.api_urls', namespace='products_api')),
    path('orders/', include('apps.orders.urls', namespace='orders')),
    path('cart/', include('apps.cart.urls', namespace='cart')),
    # path('api/', include('apps.recommendations.urls', namespace='api')),  # Phase 10
    path('accounts/', include('apps.accounts.urls', namespace='accounts')),
    path('', include('apps.products.urls', namespace='products')),
    path('', include('apps.core.urls')),
    
    # API endpoints (all prefixed with /api/)
    path('api/', include('apps.core.api_urls')),
    
    # Web app URLs
    path('', include('apps.products.urls')),
    path('', include('apps.core.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Admin site customization
admin.site.site_header = "AuroraMart Admin"
admin.site.site_title = "AuroraMart Admin Portal"
admin.site.index_title = "Welcome to AuroraMart Administration"