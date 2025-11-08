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

    # Admin Panel
    path('admin-panel/', include('apps.adminpanel.urls', namespace='adminpanel')),

    # Storefront (customer-facing)
    path('api/', include('apps.storefront.api_urls', namespace='storefront_api')),
    path('api/', include('apps.core.api_urls')),  # Recommendation APIs
    path('', include('apps.storefront.urls', namespace='storefront')),
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
