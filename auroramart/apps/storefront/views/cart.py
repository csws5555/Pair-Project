from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.generic import View
from django.db import transaction
from django.db.models import F, Sum
from decimal import Decimal

from .models import Cart, CartItem
from apps.storefront.models import Product


class CartDetailView(LoginRequiredMixin, View):
    """Display cart with all items and recommendations"""
    
    def get(self, request):
        # Get or create cart for user
        cart, created = Cart.objects.get_or_create(user=request.user)
        
        # Get all cart items with related product data
        cart_items = cart.items.select_related(
            'product',
            'product__category'
        ).prefetch_related(
            'product__images'
        )
        
        # Calculate totals
        subtotal = cart.get_subtotal()
        estimated_tax = subtotal * Decimal('0.10')  # 10% tax estimate
        estimated_shipping = Decimal('10.00') if subtotal < 50 else Decimal('0.00')
        total = subtotal + estimated_tax + estimated_shipping
        
        # Get "Complete the Set" recommendations (placeholder for ML)
        recommendations = self._get_recommendations(cart)
        
        context = {
            'cart': cart,
            'cart_items': cart_items,
            'subtotal': subtotal,
            'estimated_tax': estimated_tax,
            'estimated_shipping': estimated_shipping,
            'total': total,
            'recommendations': recommendations,
        }
        
        return render(request, 'cart/cart_detail.html', context)
    
    def _get_recommendations(self, cart):
        """
        Get product recommendations based on cart contents
        This is a placeholder for ML-based recommendations (OS-004)
        """
        if not cart.items.exists():
            return Product.objects.none()
        
        # Get categories of products in cart
        cart_categories = cart.items.values_list(
            'product__category', 
            flat=True
        ).distinct()
        
        # Get product IDs already in cart
        cart_product_ids = cart.items.values_list('product_id', flat=True)
        
        # Get related products from same categories, excluding cart items
        recommendations = Product.objects.filter(
            category__in=cart_categories,
            is_active=True,
            stock__gt=0
        ).exclude(
            id__in=cart_product_ids
        ).order_by('-rating', '-sales_count')[:6]
        
        return recommendations


@login_required
@require_POST
def add_to_cart(request):
    """Add product to cart or update quantity"""
    product_id = request.POST.get('product_id')
    quantity = int(request.POST.get('quantity', 1))
    
    # Validate inputs
    if not product_id or quantity < 1:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'error': 'Invalid product or quantity'
            }, status=400)
        messages.error(request, 'Invalid product or quantity.')
        return redirect('cart:cart_detail')
    
    # Get product
    product = get_object_or_404(Product, id=product_id, is_active=True)
    
    # Check stock availability
    if product.stock < quantity:
        error_msg = f'Only {product.stock} units available in stock.'
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'error': error_msg
            }, status=400)
        messages.error(request, error_msg)
        return redirect('products:product_detail', slug=product.slug)
    
    # Use transaction to ensure data consistency
    with transaction.atomic():
        # Get or create cart
        cart, created = Cart.objects.get_or_create(user=request.user)
        
        # Get or create cart item
        cart_item, item_created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            defaults={'quantity': quantity}
        )
        
        if not item_created:
            # Update existing item
            new_quantity = cart_item.quantity + quantity
            
            # Check if new quantity exceeds stock
            if new_quantity > product.stock:
                error_msg = f'Cannot add {quantity} more. Only {product.stock - cart_item.quantity} units available.'
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': False,
                        'error': error_msg
                    }, status=400)
                messages.error(request, error_msg)
                return redirect('products:product_detail', slug=product.slug)
            
            cart_item.quantity = new_quantity
            cart_item.save()
    
    # Success response
    success_msg = f'{product.name} added to cart successfully!'
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'message': success_msg,
            'cart_item_count': cart.items.aggregate(
                total=Sum('quantity')
            )['total'] or 0,
            'cart_total': str(cart.get_total())
        })
    
    messages.success(request, success_msg)
    return redirect('cart:cart_detail')


@login_required
@require_POST
def update_cart_item(request):
    """Update cart item quantity"""
    item_id = request.POST.get('item_id')
    quantity = request.POST.get('quantity')
    
    try:
        quantity = int(quantity)
        if quantity < 1:
            raise ValueError("Quantity must be at least 1")
    except (ValueError, TypeError):
        return JsonResponse({
            'success': False,
            'error': 'Invalid quantity'
        }, status=400)
    
    # Get cart item
    cart_item = get_object_or_404(
        CartItem,
        id=item_id,
        cart__user=request.user
    )
    
    # Check stock availability
    if quantity > cart_item.product.stock:
        return JsonResponse({
            'success': False,
            'error': f'Only {cart_item.product.stock} units available in stock.'
        }, status=400)
    
    # Update quantity
    with transaction.atomic():
        cart_item.quantity = quantity
        cart_item.save()
        
        # Get updated cart totals
        cart = cart_item.cart
        subtotal = cart.get_subtotal()
        estimated_tax = subtotal * Decimal('0.10')
        estimated_shipping = Decimal('10.00') if subtotal < 50 else Decimal('0.00')
        total = subtotal + estimated_tax + estimated_shipping
    
    return JsonResponse({
        'success': True,
        'item_total': str(cart_item.get_total()),
        'subtotal': str(subtotal),
        'estimated_tax': str(estimated_tax),
        'estimated_shipping': str(estimated_shipping),
        'total': str(total),
        'cart_item_count': cart.items.aggregate(
            total=Sum('quantity')
        )['total'] or 0
    })


@login_required
@require_POST
def remove_from_cart(request):
    """Remove item from cart"""
    item_id = request.POST.get('item_id')
    
    # Get and delete cart item
    cart_item = get_object_or_404(
        CartItem,
        id=item_id,
        cart__user=request.user
    )
    
    product_name = cart_item.product.name
    cart = cart_item.cart
    
    cart_item.delete()
    
    # Calculate updated totals
    subtotal = cart.get_subtotal()
    estimated_tax = subtotal * Decimal('0.10')
    estimated_shipping = Decimal('10.00') if subtotal < 50 else Decimal('0.00')
    total = subtotal + estimated_tax + estimated_shipping
    
    success_msg = f'{product_name} removed from cart.'
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'message': success_msg,
            'subtotal': str(subtotal),
            'estimated_tax': str(estimated_tax),
            'estimated_shipping': str(estimated_shipping),
            'total': str(total),
            'cart_item_count': cart.items.aggregate(
                total=Sum('quantity')
            )['total'] or 0
        })
    
    messages.success(request, success_msg)
    return redirect('cart:cart_detail')


@login_required
@require_POST
def clear_cart(request):
    """Clear all items from cart"""
    try:
        cart = Cart.objects.get(user=request.user)
        cart.clear()
        
        success_msg = 'Cart cleared successfully.'
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': success_msg
            })
        
        messages.success(request, success_msg)
    except Cart.DoesNotExist:
        pass
    
    return redirect('cart:cart_detail')


@login_required
@require_POST
def save_for_later(request):
    """Move item to saved for later (placeholder)"""
    item_id = request.POST.get('item_id')
    
    cart_item = get_object_or_404(
        CartItem,
        id=item_id,
        cart__user=request.user
    )
    
    # This is a placeholder - you would implement a SavedItem model
    product_name = cart_item.product.name
    cart_item.delete()
    
    success_msg = f'{product_name} saved for later.'
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'message': success_msg
        })
    
    messages.success(request, success_msg)
    return redirect('cart:cart_detail')

class CartCountView(LoginRequiredMixin, View):
    """API view to get cart item count"""
    def get(self, request):
        cart = Cart.objects.filter(user=request.user).first()
        count = 0
        if cart:
            count = cart.items.aggregate(total=Sum('quantity'))['total'] or 0
        return JsonResponse({'count': count})
