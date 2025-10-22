"""
Accounts App URL Configuration
Authentication and user profile routes
"""
from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = 'accounts'

urlpatterns = [
    # Authentication URLs
    path('register/', views.RegisterView.as_view(), name='register'),
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('logout/', views.CustomLogoutView.as_view(), name='logout'),
    
    # Profile URLs
    path('profile/', views.ProfileDashboardView.as_view(), name='profile_dashboard'),
    path('profile/edit/', views.ProfileEditView.as_view(), name='profile_edit'),
    path('profile/password/', views.CustomPasswordChangeView.as_view(), name='password_change'),
    path('profile/password/done/', auth_views.PasswordChangeDoneView.as_view(
        template_name='accounts/password_change_done.html'
    ), name='password_change_done'),
    
    # Address Management URLs
    path('profile/addresses/', views.AddressListView.as_view(), name='address_list'),
    path('profile/addresses/add/', views.AddressCreateView.as_view(), name='address_create'),
    path('profile/addresses/<int:pk>/edit/', views.AddressUpdateView.as_view(), name='address_update'),
    path('profile/addresses/<int:pk>/delete/', views.AddressDeleteView.as_view(), name='address_delete'),
    
    # Order History URL
    path('profile/orders/', views.OrderHistoryView.as_view(), name='order_history'),
    path('profile/orders/<int:pk>/', views.OrderDetailView.as_view(), name='order_detail'),

    
]