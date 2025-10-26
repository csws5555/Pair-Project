"""
Cart App URL Configuration
Shopping cart management routes
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .api_views import CartViewSet
from . import views

app_name = 'cart'

router = DefaultRouter()
router.register(r'cart', CartViewSet, basename='cart')

urlpatterns = [
    # Cart actions
    path('', views.CartDetailView.as_view(), name='cart_detail'),
    path('add/', views.add_to_cart, name='add_to_cart'),
    path('update/', views.update_cart_item, name='update_cart_item'),
    path('remove/', views.remove_from_cart, name='remove_from_cart'),
    path('clear/', views.clear_cart, name='clear_cart'),
    path('save-for-later/', views.save_for_later, name='save_for_later'),
    
    # AJAX endpoints
    path('api/count/', views.CartCountView.as_view(), name='cart_count'),

    path('', include(router.urls)),
]