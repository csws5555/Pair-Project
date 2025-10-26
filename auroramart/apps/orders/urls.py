"""
Orders App URL Configuration
Checkout and order management routes
"""
from . import views
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .api_views import OrderViewSet, AddressViewSet

app_name = 'orders'

router = DefaultRouter()
router.register(r'orders', OrderViewSet, basename='order')
router.register(r'addresses', AddressViewSet, basename='address')

urlpatterns = [
    # Checkout flow
    path('checkout/shipping/', views.ShippingAddressView.as_view(), name='checkout_shipping'),
    path('checkout/payment/', views.PaymentMethodView.as_view(), name='checkout_payment'),
    path('checkout/review/', views.OrderReviewView.as_view(), name='checkout_review'),
    path('checkout/place-order/', views.PlaceOrderView.as_view(), name='place_order'),
    path('checkout/edit/<str:step>/', views.edit_checkout_address, name='edit_checkout_address'),
    
    # Order confirmation
    path('confirmation/<str:order_number>/', views.OrderConfirmationView.as_view(), name='order_confirmation'),
    
    # Order tracking (for customers)
    path('track/<str:order_number>/', views.OrderTrackingView.as_view(), name='order_tracking'),

    path('', include(router.urls)),
]