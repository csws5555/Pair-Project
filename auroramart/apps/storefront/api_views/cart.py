from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404

from .models import Cart, CartItem
from .serializers import (
    CartSerializer,
    CartItemSerializer,
    AddToCartSerializer,
    UpdateCartItemSerializer
)
from apps.storefront.models import Product


class CartViewSet(viewsets.ViewSet):
    """
    ViewSet for managing shopping cart.
    
    All endpoints require authentication.
    
    Custom Actions:
    - list: GET /api/cart/ - Get current cart
    - add_item: POST /api/cart/add-item/ - Add item to cart
    - update_item: PATCH /api/cart/items/{id}/ - Update item quantity
    - remove_item: DELETE /api/cart/items/{id}/ - Remove item from cart
    - clear: DELETE /api/cart/clear/ - Clear all items from cart
    """
    permission_classes = [IsAuthenticated]

    def get_or_create_cart(self, user):
        """
        Helper method to get or create cart for user
        """
        cart, created = Cart.objects.get_or_create(user=user)
        return cart

    def list(self, request):
        """
        Get the current user's cart with all items.
        
        GET /api/cart/
        """
        cart = self.get_or_create_cart(request.user)
        serializer = CartSerializer(cart, context={'request': request})
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def add_item(self, request):
        """
        Add an item to the cart.
        
        POST /api/cart/add-item/
        Body: {
            "product_id": 1,
            "quantity": 2
        }
        """
        serializer = AddToCartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        product_id = serializer.validated_data['product_id']
        quantity = serializer.validated_data['quantity']
        
        cart = self.get_or_create_cart(request.user)
        product = get_object_or_404(Product, id=product_id, is_active=True)
        
        # Check if item already exists in cart
        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            defaults={'quantity': quantity}
        )
        
        if not created:
            # Item exists, update quantity
            new_quantity = cart_item.quantity + quantity
            
            # Validate stock
            if new_quantity > product.stock_quantity:
                return Response(
                    {
                        'error': f'Only {product.stock_quantity} units available. '
                                f'You currently have {cart_item.quantity} in cart.'
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            cart_item.quantity = new_quantity
            cart_item.save()
            message = 'Cart item quantity updated'
        else:
            message = 'Item added to cart'
        
        # Return updated cart
        cart_serializer = CartSerializer(cart, context={'request': request})
        return Response(
            {
                'message': message,
                'cart': cart_serializer.data
            },
            status=status.HTTP_200_OK if not created else status.HTTP_201_CREATED
        )

    @action(detail=False, methods=['patch'], url_path='items/(?P<item_id>[^/.]+)')
    def update_item(self, request, item_id=None):
        """
        Update cart item quantity.
        
        PATCH /api/cart/items/{item_id}/
        Body: {
            "quantity": 3
        }
        
        Set quantity to 0 to remove item.
        """
        cart = self.get_or_create_cart(request.user)
        cart_item = get_object_or_404(CartItem, id=item_id, cart=cart)
        
        serializer = UpdateCartItemSerializer(
            data=request.data,
            context={'cart_item': cart_item}
        )
        serializer.is_valid(raise_exception=True)
        
        quantity = serializer.validated_data['quantity']
        
        if quantity == 0:
            # Remove item if quantity is 0
            cart_item.delete()
            message = 'Item removed from cart'
        else:
            # Update quantity
            cart_item.quantity = quantity
            cart_item.save()
            message = 'Cart item quantity updated'
        
        # Return updated cart
        cart_serializer = CartSerializer(cart, context={'request': request})
        return Response(
            {
                'message': message,
                'cart': cart_serializer.data
            },
            status=status.HTTP_200_OK
        )

    @action(detail=False, methods=['delete'], url_path='items/(?P<item_id>[^/.]+)')
    def remove_item(self, request, item_id=None):
        """
        Remove an item from the cart.
        
        DELETE /api/cart/items/{item_id}/
        """
        cart = self.get_or_create_cart(request.user)
        cart_item = get_object_or_404(CartItem, id=item_id, cart=cart)
        
        product_name = cart_item.product.name
        cart_item.delete()
        
        # Return updated cart
        cart_serializer = CartSerializer(cart, context={'request': request})
        return Response(
            {
                'message': f'{product_name} removed from cart',
                'cart': cart_serializer.data
            },
            status=status.HTTP_200_OK
        )

    @action(detail=False, methods=['delete'])
    def clear(self, request):
        """
        Clear all items from the cart.
        
        DELETE /api/cart/clear/
        """
        cart = self.get_or_create_cart(request.user)
        items_count = cart.items.count()
        cart.items.all().delete()
        
        # Return updated cart
        cart_serializer = CartSerializer(cart, context={'request': request})
        return Response(
            {
                'message': f'{items_count} item(s) removed from cart',
                'cart': cart_serializer.data
            },
            status=status.HTTP_200_OK
        )

    @action(detail=False, methods=['get'])
    def count(self, request):
        """
        Get the total number of items in cart (for cart badge).
        
        GET /api/cart/count/
        """
        cart = self.get_or_create_cart(request.user)
        total_items = sum(item.quantity for item in cart.items.all())
        
        return Response(
            {
                'count': total_items
            },
            status=status.HTTP_200_OK
        )