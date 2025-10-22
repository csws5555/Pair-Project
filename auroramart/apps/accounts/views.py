"""
Accounts App Views
PHASE_2_VIEWS - STEP_2.2_AUTH_VIEWS
Authentication and user profile management views
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.views import LoginView, LogoutView, PasswordChangeView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.generic import CreateView, UpdateView, DeleteView, ListView, DetailView, TemplateView
from django.urls import reverse_lazy, reverse
from django.http import JsonResponse
from django.db.models import Q

from .forms import CustomUserCreationForm, UserUpdateForm, AddressForm
from apps.orders.models import Order, Address
from apps.recommendations.services import CategoryPredictionService


class RegisterView(CreateView):
    """
    User registration view with demographic data collection
    Fulfills: OS-007 (User Registration)
    """
    form_class = CustomUserCreationForm
    template_name = 'accounts/register.html'
    success_url = reverse_lazy('storefront:home')

    def dispatch(self, request, *args, **kwargs):
        # Redirect authenticated users
        if request.user.is_authenticated:
            return redirect('storefront:home')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        """
        On successful registration:
        1. Create user account
        2. Log user in automatically
        3. Trigger ML prediction for preferred category
        4. Redirect to personalized category landing page
        """
        # Save user
        user = form.save()
        
        # Log user in automatically
        login(self.request, user)
        messages.success(self.request, f'Welcome to AuroraMart, {user.first_name}!')
        
        # Trigger ML prediction for preferred category (async recommended in production)
        try:
            prediction_service = CategoryPredictionService()
            predicted_category = prediction_service.predict_preferred_category(user)
            
            if predicted_category:
                # Store prediction in session for personalized landing
                self.request.session['predicted_category'] = predicted_category.slug
                messages.info(
                    self.request,
                    f'Based on your profile, we think you might love our {predicted_category.name} collection!'
                )
                return redirect('storefront:personalized_category')
        except Exception as e:
            # Log error but don't break registration flow
            print(f"Category prediction error: {e}")
        
        return redirect(self.success_url)

    def form_invalid(self, form):
        """Handle form errors"""
        messages.error(self.request, 'Please correct the errors below.')
        return super().form_invalid(form)


class CustomLoginView(LoginView):
    """
    Custom login view with remember me and role-based redirects
    """
    template_name = 'accounts/login.html'
    redirect_authenticated_user = True

    def get_success_url(self):
        """
        Redirect logic:
        - Admin users → admin dashboard
        - Regular users → storefront (or next parameter)
        """
        user = self.request.user
        
        # Check for next parameter
        next_url = self.request.GET.get('next')
        if next_url:
            return next_url
        
        # Role-based redirect
        if user.is_staff or user.is_superuser:
            return reverse('admin_panel:dashboard')
        
        return reverse('storefront:home')

    def form_valid(self, form):
        """Handle remember me functionality"""
        remember_me = self.request.POST.get('remember_me')
        
        response = super().form_valid(form)
        
        if remember_me:
            # Session expires in 30 days
            self.request.session.set_expiry(2592000)  # 30 days in seconds
        else:
            # Session expires when browser closes
            self.request.session.set_expiry(0)
        
        messages.success(self.request, f'Welcome back, {self.request.user.first_name}!')
        return response


class CustomLogoutView(LogoutView):
    """
    Custom logout view with session cleanup
    """
    next_page = 'storefront:home'

    def dispatch(self, request, *args, **kwargs):
        """Clear session data on logout"""
        if request.user.is_authenticated:
            messages.info(request, 'You have been logged out successfully.')
        return super().dispatch(request, *args, **kwargs)


class ProfileDashboardView(LoginRequiredMixin, TemplateView):
    """
    User profile dashboard with tabbed interface
    Fulfills: OS-011 (User Profile Management)
    """
    template_name = 'accounts/profile_dashboard.html'
    login_url = 'accounts:login'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        context.update({
            'user': user,
            'addresses': Address.objects.filter(user=user).order_by('-is_default', '-created_at'),
            'recent_orders': Order.objects.filter(user=user).order_by('-created_at')[:5],
            'total_orders': Order.objects.filter(user=user).count(),
            'active_tab': self.request.GET.get('tab', 'overview'),
        })
        
        return context


class ProfileEditView(LoginRequiredMixin, UpdateView):
    """
    Edit user profile information
    Fulfills: OS-011 (User Profile Management)
    """
    form_class = UserUpdateForm
    template_name = 'accounts/profile_edit.html'
    success_url = reverse_lazy('accounts:profile_dashboard')
    login_url = 'accounts:login'

    def get_object(self, queryset=None):
        """Return the current user"""
        return self.request.user

    def form_valid(self, form):
        messages.success(self.request, 'Your profile has been updated successfully.')
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, 'Please correct the errors below.')
        return super().form_invalid(form)


class CustomPasswordChangeView(LoginRequiredMixin, PasswordChangeView):
    """
    Change user password
    """
    template_name = 'accounts/password_change.html'
    success_url = reverse_lazy('accounts:password_change_done')
    login_url = 'accounts:login'

    def form_valid(self, form):
        messages.success(self.request, 'Your password has been changed successfully.')
        return super().form_valid(form)


class AddressListView(LoginRequiredMixin, ListView):
    """
    List user's addresses
    Fulfills: OS-011 (Address Management)
    """
    model = Address
    template_name = 'accounts/address_list.html'
    context_object_name = 'addresses'
    login_url = 'accounts:login'

    def get_queryset(self):
        """Return only current user's addresses"""
        return Address.objects.filter(user=self.request.user).order_by('-is_default', '-created_at')


class AddressCreateView(LoginRequiredMixin, CreateView):
    """
    Create new address
    Fulfills: OS-011 (Address Management)
    """
    model = Address
    form_class = AddressForm
    template_name = 'accounts/address_form.html'
    success_url = reverse_lazy('accounts:address_list')
    login_url = 'accounts:login'

    def get_form_kwargs(self):
        """Pass user to form"""
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, 'Address added successfully.')
        return super().form_valid(form)


class AddressUpdateView(LoginRequiredMixin, UpdateView):
    """
    Update existing address
    Fulfills: OS-011 (Address Management)
    """
    model = Address
    form_class = AddressForm
    template_name = 'accounts/address_form.html'
    success_url = reverse_lazy('accounts:address_list')
    login_url = 'accounts:login'

    def get_queryset(self):
        """Ensure user can only update their own addresses"""
        return Address.objects.filter(user=self.request.user)

    def get_form_kwargs(self):
        """Pass user to form"""
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, 'Address updated successfully.')
        return super().form_valid(form)


class AddressDeleteView(LoginRequiredMixin, DeleteView):
    """
    Delete address
    Fulfills: OS-011 (Address Management)
    """
    model = Address
    template_name = 'accounts/address_confirm_delete.html'
    success_url = reverse_lazy('accounts:address_list')
    login_url = 'accounts:login'

    def get_queryset(self):
        """Ensure user can only delete their own addresses"""
        return Address.objects.filter(user=self.request.user)

    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Address deleted successfully.')
        return super().delete(request, *args, **kwargs)


class OrderHistoryView(LoginRequiredMixin, ListView):
    """
    Display user's order history
    Fulfills: OS-011 (Order History)
    """
    model = Order
    template_name = 'accounts/order_history.html'
    context_object_name = 'orders'
    paginate_by = 10
    login_url = 'accounts:login'

    def get_queryset(self):
        """Return current user's orders"""
        queryset = Order.objects.filter(user=self.request.user).order_by('-created_at')
        
        # Filter by status if provided
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        # Search by order number
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(order_number__icontains=search)
        
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['status_choices'] = Order.STATUS_CHOICES
        context['current_status'] = self.request.GET.get('status', '')
        context['search_query'] = self.request.GET.get('search', '')
        return context


class OrderDetailView(LoginRequiredMixin, DetailView):
    """
    Display detailed order information
    Fulfills: OS-011 (Order History)
    """
    model = Order
    template_name = 'accounts/order_detail.html'
    context_object_name = 'order'
    login_url = 'accounts:login'

    def get_queryset(self):
        """Ensure user can only view their own orders"""
        return Order.objects.filter(user=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['order_items'] = self.object.items.all().select_related('product')
        return context