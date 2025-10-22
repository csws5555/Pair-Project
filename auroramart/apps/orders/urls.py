"""
Orders App URL Configuration
Checkout and order management routes
"""
from django.urls import path
from . import views

app_name = 'orders'

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
]