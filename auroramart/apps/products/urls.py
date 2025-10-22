"""
Products App URL Configuration
Storefront browsing routes
"""
from django.urls import path
from . import views

app_name = 'storefront'

urlpatterns = [
    # Homepage
    path('', views.HomeView.as_view(), name='home'),

    # Category browsing
    path('category/<slug:slug>/', views.CategoryBrowseView.as_view(), name='category_detail'),

    # Product browsing
    path('product/<slug:slug>/', views.ProductDetailView.as_view(), name='product_detail'),

    # Search
    path('search/', views.ProductSearchView.as_view(), name='product_search'),

    # Personalized category landing
    path('personalized/', views.PersonalizedCategoryView.as_view(), name='personalized_category'),

    # Product Management
    path('admin/products/', views.ProductListView.as_view(), name='admin_product_list'),
    path('admin/products/add/', views.ProductCreateView.as_view(), name='admin_product_add'),
    path('admin/products/<int:pk>/edit/', views.ProductUpdateView.as_view(), name='admin_product_edit'),
    path('admin/products/<int:pk>/delete/', views.ProductDeleteView.as_view(), name='admin_product_delete'),
    path('admin/products/bulk-action/', views.ProductBulkActionView.as_view(), name='admin_product_bulk_action'),

    # Import/Export
    path('admin/products/export/', views.ProductExportView.as_view(), name='admin_product_export'),
    path('admin/products/import/', views.ProductImportView.as_view(), name='admin_product_import'),
    path('admin/products/import/confirm/', views.ProductImportConfirmView.as_view(), name='admin_product_import_confirm'),

    # Inventory Management
    path('admin/inventory/', views.InventoryDashboardView.as_view(), name='admin_inventory_dashboard'),
    path('admin/inventory/<int:pk>/adjust/', views.StockAdjustmentView.as_view(), name='admin_stock_adjust'),
    path('admin/inventory/<int:pk>/threshold/', views.ReorderThresholdUpdateView.as_view(), name='admin_reorder_threshold'),
    path('admin/inventory/report/', views.InventoryReportView.as_view(), name='admin_inventory_report'),
]