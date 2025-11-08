from rest_framework import viewsets, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404

from .models import Order, Address
from .serializers import (
    OrderListSerializer,
    OrderDetailSerializer,
    CreateOrderSerializer,
    AddressSerializer,
    OrderStatusUpdateSerializer
)


class OrderViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing orders.
    
    Users can only view their own orders.
    
    Provides:
    - list: GET /api/orders/ - List user's orders
    - retrieve: GET /api/orders/{order_number}/ - Get order detail
    """
    permission_classes = [IsAuthenticated]
    lookup_field = 'order_number'

    def get_queryset(self):
        """
        Filter orders to only show current user's orders
        """
        user = self.request.user
        if user.is_staff:
            # Admin can see all orders
            return Order.objects.all().select_related(
                'user', 'shipping_address', 'billing_address'
            ).prefetch_related('items')
        
        # Regular users only see their own orders
        return Order.objects.filter(user=user).select_related(
            'shipping_address', 'billing_address'
        ).prefetch_related('items')

    def get_serializer_class(self):
        """
        Use different serializers for list vs detail views
        """
        if self.action == 'retrieve':
            return OrderDetailSerializer
        return OrderListSerializer

    @action(detail=True, methods=['patch'], permission_classes=[IsAdminUser])
    def update_status(self, request, order_number=None):
        """
        Update order status (admin only).
        
        PATCH /api/orders/{order_number}/update-status/
        Body: {
            "status": "shipped",
            "tracking_number": "TRACK123456"
        }
        """
        order = self.get_object()
        
        serializer = OrderStatusUpdateSerializer(
            data=request.data,
            context={'instance': order}
        )
        serializer.is_valid(raise_exception=True)
        
        order.status = serializer.validated_data['status']
        if 'tracking_number' in serializer.validated_data:
            order.tracking_number = serializer.validated_data['tracking_number']
        
        order.save()
        
        detail_serializer = OrderDetailSerializer(order, context={'request': request})
        return Response(
            {
                'message': 'Order status updated successfully',
                'order': detail_serializer.data
            },
            status=status.HTTP_200_OK
        )

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """
        Get user's order statistics.
        
        GET /api/orders/statistics/
        """
        queryset = self.get_queryset()
        
        total_orders = queryset.count()
        total_spent = sum(order.total for order in queryset)
        
        status_counts = {}
        for order in queryset:
            status_counts[order.status] = status_counts.get(order.status, 0) + 1
        
        return Response({
            'total_orders': total_orders,
            'total_spent': float(total_spent),
            'orders_by_status': status_counts
        })


class CheckoutAPIView(APIView):
    """
    API view for checkout process.
    
    POST /api/checkout/
    
    Creates an order from user's cart.
    Requires authentication.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        Create an order from cart.
        
        Body: {
            "shipping_address_id": 1,  // OR shipping_address object
            "billing_address_id": 2,   // OR billing_address object OR use_shipping_for_billing
            "payment_method": "credit_card",
            "use_shipping_for_billing": false,
            "notes": "Please call before delivery"
        }
        """
        serializer = CreateOrderSerializer(
            data=request.data,
            context={'request': request}
        )
        
        try:
            serializer.is_valid(raise_exception=True)
            order = serializer.save()
            
            # Return created order details
            order_serializer = OrderDetailSerializer(order, context={'request': request})
            
            return Response(
                {
                    'message': 'Order created successfully',
                    'order': order_serializer.data
                },
                status=status.HTTP_201_CREATED
            )
        
        except Exception as e:
            return Response(
                {
                    'error': 'Failed to create order',
                    'details': str(e)
                },
                status=status.HTTP_400_BAD_REQUEST
            )


class AddressViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing user addresses.
    
    Provides full CRUD operations for addresses.
    Users can only manage their own addresses.
    
    Endpoints:
    - list: GET /api/addresses/
    - create: POST /api/addresses/
    - retrieve: GET /api/addresses/{id}/
    - update: PUT /api/addresses/{id}/
    - partial_update: PATCH /api/addresses/{id}/
    - destroy: DELETE /api/addresses/{id}/
    """
    serializer_class = AddressSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Filter addresses to only show current user's addresses
        """
        return Address.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        """
        Set the user when creating an address
        """
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['post'])
    def set_default(self, request, pk=None):
        """
        Set an address as default for its type.
        
        POST /api/addresses/{id}/set-default/
        """
        address = self.get_object()
        
        # Remove default flag from other addresses of same type
        Address.objects.filter(
            user=request.user,
            address_type=address.address_type,
            is_default=True
        ).update(is_default=False)
        
        # Set this address as default
        address.is_default = True
        address.save()
        
        serializer = AddressSerializer(address, context={'request': request})
        return Response(
            {
                'message': f'Default {address.address_type} address updated',
                'address': serializer.data
            },
            status=status.HTTP_200_OK
        )

    @action(detail=False, methods=['get'])
    def default_shipping(self, request):
        """
        Get user's default shipping address.
        
        GET /api/addresses/default-shipping/
        """
        address = Address.objects.filter(
            user=request.user,
            address_type='shipping',
            is_default=True
        ).first()
        
        if not address:
            return Response(
                {'message': 'No default shipping address found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = AddressSerializer(address, context={'request': request})
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def default_billing(self, request):
        """
        Get user's default billing address.
        
        GET /api/addresses/default-billing/
        """
        address = Address.objects.filter(
            user=request.user,
            address_type='billing',
            is_default=True
        ).first()
        
        if not address:
            return Response(
                {'message': 'No default billing address found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = AddressSerializer(address, context={'request': request})
        return Response(serializer.data)