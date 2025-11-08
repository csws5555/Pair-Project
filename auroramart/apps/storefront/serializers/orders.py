from rest_framework import serializers
from django.db import transaction
from decimal import Decimal
from ..models import Order, OrderItem, Address
from apps.storefront.models import Cart, CartItem
from apps.storefront.models import Product


class AddressSerializer(serializers.ModelSerializer):
    """
    Serializer for Address model
    """
    class Meta:
        model = Address
        fields = [
            'id', 'address_type', 'full_name', 'phone', 'street_address',
            'apartment', 'city', 'state', 'postal_code', 'country',
            'is_default', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_phone(self, value):
        """
        Validate phone number format (basic validation)
        """
        if value and len(value) < 10:
            raise serializers.ValidationError("Phone number must be at least 10 digits.")
        return value

    def validate_postal_code(self, value):
        """
        Validate postal code is not empty
        """
        if not value or not value.strip():
            raise serializers.ValidationError("Postal code is required.")
        return value.strip()


class OrderItemSerializer(serializers.ModelSerializer):
    """
    Serializer for Order Items (read-only)
    """
    class Meta:
        model = OrderItem
        fields = [
            'id', 'product_name', 'product_sku', 'price',
            'quantity', 'total_price'
        ]
        read_only_fields = ['id']


class OrderListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for order listings
    """
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'status', 'status_display',
            'total', 'created_at'
        ]
        read_only_fields = ['id', 'order_number', 'created_at']


class OrderDetailSerializer(serializers.ModelSerializer):
    """
    Detailed serializer for single order view
    """
    items = OrderItemSerializer(many=True, read_only=True)
    shipping_address = AddressSerializer(read_only=True)
    billing_address = AddressSerializer(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    payment_method_display = serializers.CharField(
        source='get_payment_method_display',
        read_only=True
    )

    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'user', 'status', 'status_display',
            'payment_method', 'payment_method_display', 'payment_status',
            'subtotal', 'tax', 'shipping_cost', 'total',
            'shipping_address', 'billing_address', 'items',
            'notes', 'tracking_number', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'order_number', 'user', 'subtotal', 'tax',
            'shipping_cost', 'total', 'created_at', 'updated_at'
        ]


class CreateOrderSerializer(serializers.Serializer):
    """
    Custom serializer for checkout process
    """
    shipping_address_id = serializers.IntegerField(required=False, allow_null=True)
    billing_address_id = serializers.IntegerField(required=False, allow_null=True)
    shipping_address = AddressSerializer(required=False, allow_null=True)
    billing_address = AddressSerializer(required=False, allow_null=True)
    payment_method = serializers.ChoiceField(
        choices=['credit_card', 'debit_card', 'paypal', 'bank_transfer', 'cash_on_delivery']
    )
    use_shipping_for_billing = serializers.BooleanField(default=False)
    notes = serializers.CharField(required=False, allow_blank=True, max_length=500)

    def validate(self, attrs):
        """
        Validate address information
        """
        user = self.context['request'].user
        shipping_address_id = attrs.get('shipping_address_id')
        billing_address_id = attrs.get('billing_address_id')
        shipping_address_data = attrs.get('shipping_address')
        billing_address_data = attrs.get('billing_address')
        use_shipping_for_billing = attrs.get('use_shipping_for_billing')

        # Validate shipping address
        if not shipping_address_id and not shipping_address_data:
            raise serializers.ValidationError(
                "Either shipping_address_id or shipping_address data is required."
            )

        if shipping_address_id:
            try:
                shipping_address = Address.objects.get(id=shipping_address_id, user=user)
                attrs['shipping_address_obj'] = shipping_address
            except Address.DoesNotExist:
                raise serializers.ValidationError("Invalid shipping address.")

        # Validate billing address
        if not use_shipping_for_billing:
            if not billing_address_id and not billing_address_data:
                raise serializers.ValidationError(
                    "Either billing_address_id or billing_address data is required when not using shipping address for billing."
                )

            if billing_address_id:
                try:
                    billing_address = Address.objects.get(id=billing_address_id, user=user)
                    attrs['billing_address_obj'] = billing_address
                except Address.DoesNotExist:
                    raise serializers.ValidationError("Invalid billing address.")

        return attrs

    def create(self, validated_data):
        """
        Create order with transaction logic
        """
        user = self.context['request'].user

        # Get or create addresses
        shipping_address = self._get_or_create_address(
            validated_data, 'shipping', user
        )
        
        if validated_data.get('use_shipping_for_billing'):
            billing_address = shipping_address
        else:
            billing_address = self._get_or_create_address(
                validated_data, 'billing', user
            )

        # Get user's cart
        try:
            cart = Cart.objects.get(user=user)
        except Cart.DoesNotExist:
            raise serializers.ValidationError("Cart is empty.")

        cart_items = cart.items.select_related('product').all()
        
        if not cart_items.exists():
            raise serializers.ValidationError("Cart is empty.")

        # Create order with transaction
        with transaction.atomic():
            # Calculate totals
            subtotal = sum(
                item.product.price * item.quantity for item in cart_items
            )
            tax = subtotal * Decimal('0.10')  # 10% tax (adjust as needed)
            shipping_cost = Decimal('10.00')  # Flat shipping (adjust as needed)
            total = subtotal + tax + shipping_cost

            # Create order
            order = Order.objects.create(
                user=user,
                shipping_address=shipping_address,
                billing_address=billing_address,
                payment_method=validated_data['payment_method'],
                subtotal=subtotal,
                tax=tax,
                shipping_cost=shipping_cost,
                total=total,
                notes=validated_data.get('notes', '')
            )

            # Create order items and update stock
            for cart_item in cart_items:
                product = cart_item.product

                # Check stock availability
                if product.stock_quantity < cart_item.quantity:
                    raise serializers.ValidationError(
                        f"Insufficient stock for {product.name}. "
                        f"Only {product.stock_quantity} available."
                    )

                # Create order item
                OrderItem.objects.create(
                    order=order,
                    product=product,
                    product_name=product.name,
                    product_sku=product.sku,
                    price=product.price,
                    quantity=cart_item.quantity
                )

                # Update stock
                product.stock_quantity -= cart_item.quantity
                product.save(update_fields=['stock_quantity'])

            # Clear cart
            cart_items.delete()

        return order

    def _get_or_create_address(self, validated_data, address_type, user):
        """
        Helper method to get existing address or create new one
        """
        address_obj_key = f'{address_type}_address_obj'
        address_data_key = f'{address_type}_address'

        if address_obj_key in validated_data:
            return validated_data[address_obj_key]
        elif address_data_key in validated_data:
            address_data = validated_data[address_data_key]
            address_data['user'] = user
            address_data['address_type'] = address_type
            address_serializer = AddressSerializer(data=address_data)
            address_serializer.is_valid(raise_exception=True)
            return address_serializer.save()
        else:
            raise serializers.ValidationError(f"{address_type.capitalize()} address is required.")


class OrderStatusUpdateSerializer(serializers.Serializer):
    """
    Serializer for updating order status (admin only)
    """
    status = serializers.ChoiceField(
        choices=['pending', 'processing', 'shipped', 'delivered', 'cancelled']
    )
    tracking_number = serializers.CharField(required=False, allow_blank=True, max_length=100)

    def validate(self, attrs):
        """
        Validate status transition
        """
        instance = self.context.get('instance')
        new_status = attrs.get('status')

        if instance:
            # Prevent certain status transitions
            if instance.status == 'delivered' and new_status != 'delivered':
                raise serializers.ValidationError(
                    "Cannot change status of delivered order."
                )
            if instance.status == 'cancelled' and new_status != 'cancelled':
                raise serializers.ValidationError(
                    "Cannot change status of cancelled order."
                )

        return attrs