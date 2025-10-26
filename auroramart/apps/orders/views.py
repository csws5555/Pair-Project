from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.views.generic import View, DetailView
from django.db import transaction
from django.urls import reverse
from django.utils import timezone
from decimal import Decimal
from datetime import timedelta

from .models import Order, OrderItem, Address, StockMovement
from .forms import (
    ShippingAddressForm, 
    BillingAddressForm, 
    PaymentMethodForm,
    OrderReviewForm
)
from apps.cart.models import Cart, CartItem
from apps.products.models import Product


class CheckoutBaseView(LoginRequiredMixin, View):
    """Base view for checkout process with common functionality"""
    
    def dispatch(self, request, *args, **kwargs):
        # Validate cart is not empty
        try:
            cart = Cart.objects.get(user=request.user)
            if not cart.items.exists():
                messages.warning(request, 'Your cart is empty.')
                return redirect('cart:cart_detail')
        except Cart.DoesNotExist:
            messages.warning(request, 'Your cart is empty.')
            return redirect('cart:cart_detail')
        
        return super().dispatch(request, *args, **kwargs)
    
    def get_or_create_checkout_session(self):
        """Initialize checkout session if not exists"""
        if 'checkout' not in self.request.session:
            self.request.session['checkout'] = {
                'shipping_address': None,
                'billing_address': None,
                'use_different_billing': False,
                'payment_method': None,
                'step': 1
            }
        return self.request.session['checkout']
    
    def get_cart_summary(self):
        """Get cart totals and items"""
        cart = Cart.objects.get(user=self.request.user)
        cart_items = cart.items.select_related('product').all()
        
        subtotal = cart.get_subtotal()
        tax = subtotal * Decimal('0.10')  # 10% tax
        shipping = Decimal('10.00') if subtotal < 50 else Decimal('0.00')
        total = subtotal + tax + shipping
        
        return {
            'cart': cart,
            'cart_items': cart_items,
            'subtotal': subtotal,
            'tax': tax,
            'shipping': shipping,
            'total': total
        }


class ShippingAddressView(CheckoutBaseView):
    """Step 1: Shipping Address"""
    
    def get(self, request):
        checkout_session = self.get_or_create_checkout_session()
        cart_summary = self.get_cart_summary()
        
        # Get user's saved addresses
        saved_addresses = Address.objects.filter(
            user=request.user,
            address_type='shipping'
        ).order_by('-is_default', '-created_at')
        
        # Initialize form
        initial_data = checkout_session.get('shipping_address')
        form = ShippingAddressForm(initial=initial_data) if initial_data else ShippingAddressForm()
        
        context = {
            'form': form,
            'saved_addresses': saved_addresses,
            'checkout_step': 1,
            **cart_summary
        }
        
        return render(request, 'orders/checkout_shipping.html', context)
    
    def post(self, request):
        checkout_session = self.get_or_create_checkout_session()
        
        # Check if user selected a saved address
        selected_address_id = request.POST.get('selected_address')
        
        if selected_address_id:
            # Use saved address
            address = get_object_or_404(
                Address, 
                id=selected_address_id, 
                user=request.user
            )
            
            address_data = {
                'name': address.name,
                'phone': getattr(address, 'phone', ''),
                'line1': address.line1,
                'line2': address.line2,
                'city': address.city,
                'state': address.state,
                'postal_code': address.postal_code,
                'country': address.country,
            }
            
            use_different_billing = request.POST.get('use_different_billing') == 'on'
            
            # Update session
            checkout_session['shipping_address'] = address_data
            checkout_session['shipping_address_id'] = selected_address_id
            checkout_session['use_different_billing'] = use_different_billing
            checkout_session['step'] = 2
            request.session.modified = True
            
            return redirect('orders:checkout_payment')
        
        else:
            # New address form submission
            form = ShippingAddressForm(request.POST)
            
            if form.is_valid():
                # Save address data to session
                address_data = {
                    'name': form.cleaned_data['name'],
                    'phone': form.cleaned_data['phone'],
                    'line1': form.cleaned_data['line1'],
                    'line2': form.cleaned_data['line2'],
                    'city': form.cleaned_data['city'],
                    'state': form.cleaned_data['state'],
                    'postal_code': form.cleaned_data['postal_code'],
                    'country': form.cleaned_data['country'],
                }
                
                checkout_session['shipping_address'] = address_data
                checkout_session['use_different_billing'] = form.cleaned_data['use_different_billing']
                checkout_session['save_shipping_address'] = form.cleaned_data['save_address']
                checkout_session['step'] = 2
                request.session.modified = True
                
                return redirect('orders:checkout_payment')
            
            else:
                # Form has errors
                cart_summary = self.get_cart_summary()
                saved_addresses = Address.objects.filter(
                    user=request.user,
                    address_type='shipping'
                ).order_by('-is_default', '-created_at')
                
                context = {
                    'form': form,
                    'saved_addresses': saved_addresses,
                    'checkout_step': 1,
                    **cart_summary
                }
                
                return render(request, 'orders/checkout_shipping.html', context)


class PaymentMethodView(CheckoutBaseView):
    """Step 2: Payment Method"""
    
    def dispatch(self, request, *args, **kwargs):
        result = super().dispatch(request, *args, **kwargs)
        
        # Ensure shipping address is completed
        checkout_session = request.session.get('checkout', {})
        if not checkout_session.get('shipping_address'):
            messages.warning(request, 'Please complete shipping address first.')
            return redirect('orders:checkout_shipping')
        
        return result
    
    def get(self, request):
        checkout_session = self.get_or_create_checkout_session()
        cart_summary = self.get_cart_summary()
        
        # Initialize forms
        payment_form = PaymentMethodForm()
        billing_form = None
        
        if checkout_session.get('use_different_billing'):
            billing_form = BillingAddressForm(
                initial=checkout_session.get('billing_address')
            )
        
        context = {
            'payment_form': payment_form,
            'billing_form': billing_form,
            'use_different_billing': checkout_session.get('use_different_billing'),
            'checkout_step': 2,
            **cart_summary
        }
        
        return render(request, 'orders/checkout_payment.html', context)
    
    def post(self, request):
        checkout_session = self.get_or_create_checkout_session()
        
        payment_form = PaymentMethodForm(request.POST)
        billing_form = None
        
        if checkout_session.get('use_different_billing'):
            billing_form = BillingAddressForm(request.POST)
        
        # Validate forms
        forms_valid = payment_form.is_valid()
        if billing_form:
            forms_valid = forms_valid and billing_form.is_valid()
        
        if forms_valid:
            # Store payment method (last 4 digits only for security)
            card_number = payment_form.cleaned_data['card_number']
            payment_data = {
                'card_last4': card_number[-4:],
                'card_name': payment_form.cleaned_data['card_name'],
                'card_type': self._detect_card_type(card_number),
                'expiry_month': payment_form.cleaned_data['expiry_month'],
                'expiry_year': payment_form.cleaned_data['expiry_year'],
            }
            
            checkout_session['payment_method'] = payment_data
            checkout_session['save_payment_method'] = payment_form.cleaned_data['save_payment_method']
            
            # Store billing address if different
            if billing_form:
                billing_data = {
                    'name': billing_form.cleaned_data['name'],
                    'phone': billing_form.cleaned_data['phone'],
                    'line1': billing_form.cleaned_data['line1'],
                    'line2': billing_form.cleaned_data['line2'],
                    'city': billing_form.cleaned_data['city'],
                    'state': billing_form.cleaned_data['state'],
                    'postal_code': billing_form.cleaned_data['postal_code'],
                    'country': billing_form.cleaned_data['country'],
                }
                checkout_session['billing_address'] = billing_data
                checkout_session['save_billing_address'] = billing_form.cleaned_data['save_address']
            else:
                # Use shipping address as billing
                checkout_session['billing_address'] = checkout_session['shipping_address']
            
            checkout_session['step'] = 3
            request.session.modified = True
            
            return redirect('orders:checkout_review')
        
        else:
            # Forms have errors
            cart_summary = self.get_cart_summary()
            
            context = {
                'payment_form': payment_form,
                'billing_form': billing_form,
                'use_different_billing': checkout_session.get('use_different_billing'),
                'checkout_step': 2,
                **cart_summary
            }
            
            return render(request, 'orders/checkout_payment.html', context)
    
    def _detect_card_type(self, card_number):
        """Detect card type from card number"""
        if card_number[0] == '4':
            return 'Visa'
        elif card_number[0] == '5':
            return 'MasterCard'
        elif card_number[0] == '3':
            return 'American Express'
        elif card_number[0] == '6':
            return 'Discover'
        return 'Unknown'


class OrderReviewView(CheckoutBaseView):
    """Step 3: Order Review"""
    
    def dispatch(self, request, *args, **kwargs):
        result = super().dispatch(request, *args, **kwargs)
        
        # Ensure previous steps are completed
        checkout_session = request.session.get('checkout', {})
        if not checkout_session.get('shipping_address') or not checkout_session.get('payment_method'):
            messages.warning(request, 'Please complete all checkout steps.')
            return redirect('orders:checkout_shipping')
        
        return result
    
    def get(self, request):
        checkout_session = self.get_or_create_checkout_session()
        cart_summary = self.get_cart_summary()
        
        form = OrderReviewForm()
        
        context = {
            'form': form,
            'checkout_session': checkout_session,
            'checkout_step': 3,
            **cart_summary
        }
        
        return render(request, 'orders/checkout_review.html', context)
    
    def post(self, request):
        # This is handled by PlaceOrderView
        return redirect('orders:place_order')


class PlaceOrderView(CheckoutBaseView):
    """Process and place the order"""
    
    def post(self, request):
        checkout_session = request.session.get('checkout', {})
        
        # Validate checkout session
        if not checkout_session.get('shipping_address') or not checkout_session.get('payment_method'):
            messages.error(request, 'Invalid checkout session. Please start over.')
            return redirect('orders:checkout_shipping')
        
        # Validate terms acceptance
        form = OrderReviewForm(request.POST)
        if not form.is_valid():
            messages.error(request, 'You must accept the terms and conditions.')
            return redirect('orders:checkout_review')
        
        try:
            with transaction.atomic():
                # Get cart and items
                cart = Cart.objects.select_for_update().get(user=request.user)
                cart_items = cart.items.select_related('product').all()
                
                if not cart_items.exists():
                    raise ValueError('Cart is empty')
                
                # Calculate totals
                subtotal = cart.get_subtotal()
                tax = subtotal * Decimal('0.10')
                shipping = Decimal('10.00') if subtotal < 50 else Decimal('0.00')
                total = subtotal + tax + shipping
                
                # Create order
                order = Order.objects.create(
                    user=request.user,
                    status='pending',
                    subtotal=subtotal,
                    tax=tax,
                    shipping_cost=shipping,
                    total=total,

                    # Shipping address
                    shipping_name=checkout_session['shipping_address']['name'],
                    shipping_line1=checkout_session['shipping_address']['line1'],
                    shipping_line2=checkout_session['shipping_address'].get('line2', ''),
                    shipping_city=checkout_session['shipping_address']['city'],
                    shipping_state=checkout_session['shipping_address']['state'],
                    shipping_postal_code=checkout_session['shipping_address']['postal_code'],
                    shipping_country=checkout_session['shipping_address']['country'],

                    # Billing address
                    billing_name=checkout_session['billing_address']['name'],
                    billing_line1=checkout_session['billing_address']['line1'],
                    billing_line2=checkout_session['billing_address'].get('line2', ''),
                    billing_city=checkout_session['billing_address']['city'],
                    billing_state=checkout_session['billing_address']['state'],
                    billing_postal_code=checkout_session['billing_address']['postal_code'],
                    billing_country=checkout_session['billing_address']['country'],

                    # Payment method (masked)
                    payment_method=checkout_session['payment_method']['card_type'],
                    payment_transaction_id=f"**** **** **** {checkout_session['payment_method']['card_last4']}"
                )
                
                # Create order items (snapshot product data)
                for cart_item in cart_items:
                    product = cart_item.product
                    
                    # Validate stock
                    if product.stock < cart_item.quantity:
                        raise ValueError(
                            f'Insufficient stock for {product.name}. '
                            f'Only {product.stock} available.'
                        )
                    
                    # Create order item
                    OrderItem.objects.create(
                        order=order,
                        product=product,
                        quantity=cart_item.quantity,
                        price=product.price,
                        # Snapshot product data
                        product_name=product.name,
                        product_sku=product.sku,
                    )
                    
                    # Update product stock
                    product.stock -= cart_item.quantity
                    product.save(update_fields=['stock'])
                    
                    # Create stock movement record
                    StockMovement.objects.create(
                        product=product,
                        quantity=-cart_item.quantity,
                        movement_type='sale',
                        reference_number=order.order_number,
                        notes=f'Order {order.order_number}'
                    )
                
                # Mock payment processing
                payment_success = self._process_payment(
                    order, 
                    checkout_session['payment_method']
                )
                
                if not payment_success:
                    raise ValueError('Payment processing failed')
                
                # Update order status
                order.status = 'confirmed'
                order.save(update_fields=['status'])
                
                # Save addresses if requested
                if checkout_session.get('save_shipping_address'):
                    self._save_address(
                        request.user,
                        checkout_session['shipping_address'],
                        'shipping'
                    )
                
                if checkout_session.get('use_different_billing') and checkout_session.get('save_billing_address'):
                    self._save_address(
                        request.user,
                        checkout_session['billing_address'],
                        'billing'
                    )
                
                # Clear cart
                cart.clear()
                
                # Store order ID in session for confirmation page
                request.session['last_order_id'] = order.id
                
                # Clear checkout session
                if 'checkout' in request.session:
                    del request.session['checkout']
                
                request.session.modified = True
                
                # Success message
                messages.success(
                    request,
                    f'Order placed successfully! Order number: {order.order_number}'
                )
                
                return redirect('orders:order_confirmation', order_number=order.order_number)
        
        except ValueError as e:
            messages.error(request, str(e))
            return redirect('orders:checkout_review')
        
        except Exception as e:
            messages.error(request, 'An error occurred while processing your order. Please try again.')
            # Log the error
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f'Order processing error: {str(e)}', exc_info=True)
            return redirect('orders:checkout_review')
    
    def _process_payment(self, order, payment_method):
        """
        Mock payment processing
        In production, integrate with real payment gateway (Stripe, PayPal, etc.)
        """
        # Simulate payment processing
        import time
        time.sleep(0.5)  # Simulate API call
        
        # In real implementation:
        # - Integrate with payment gateway API
        # - Handle payment webhooks
        # - Store payment transaction ID
        # - Handle payment failures and retries
        
        return True  # Mock success
    
    def _save_address(self, user, address_data, address_type):
        """Save address to user's address book"""
        Address.objects.create(
            user=user,
            address_type=address_type,
            name=address_data['name'],
            line1=address_data['line1'],
            line2=address_data.get('line2', ''),
            city=address_data['city'],
            state=address_data['state'],
            postal_code=address_data['postal_code'],
            country=address_data['country'],
        )


class OrderConfirmationView(LoginRequiredMixin, View):
    """Display order confirmation"""
    
    def get(self, request, order_number):
        # Get order
        order = get_object_or_404(
            Order,
            order_number=order_number,
            user=request.user
        )
        
        # Get order items
        order_items = order.items.select_related('product').all()
        
        # Calculate estimated delivery
        estimated_delivery = timezone.now() + timedelta(days=7)
        
        context = {
            'order': order,
            'order_items': order_items,
            'estimated_delivery': estimated_delivery,
        }
        
        return render(request, 'orders/order_confirmation.html', context)


# Additional helper view for editing addresses during checkout
@login_required
def edit_checkout_address(request, step):
    """Edit address during checkout"""
    if step == 'shipping':
        return redirect('orders:checkout_shipping')
    elif step == 'payment':
        return redirect('orders:checkout_payment')
    else:
        return redirect('orders:checkout_review')


class OrderTrackingView(LoginRequiredMixin, DetailView):
    """View for tracking order status"""
    model = Order
    template_name = 'orders/order_tracking.html'
    context_object_name = 'order'
    slug_field = 'order_number'
    slug_url_kwarg = 'order_number'

    def get_queryset(self):
        # Ensure users can only track their own orders
        return Order.objects.filter(user=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        order = self.get_object()
        context['order_items'] = order.items.select_related('product').all()

        # Calculate progress percentage
        status_progress = {
            'pending': 25,
            'processing': 50,
            'shipped': 75,
            'delivered': 100,
            'cancelled': 0
        }
        context['progress'] = status_progress.get(order.status, 0)

        return context