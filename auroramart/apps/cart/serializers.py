from rest_framework import serializers
from .models import Cart, CartItem
from apps.products.serializers import ProductListSerializer
from apps.products.models import Product


class CartItemSerializer(serializers.ModelSerializer):
    """
    Serializer for Cart Items with product details and validation
    """
    product_detail = ProductListSerializer(source='product', read_only=True)
    total_price = serializers.SerializerMethodField()

    class Meta:
        model = CartItem
        fields = ['id', 'product', 'quantity', 'total_price', 'product_detail']
        read_only_fields = ['id', 'total_price']

    def get_total_price(self, obj):
        """
        Calculate total price for this cart item
        """
        return obj.product.price * obj.quantity

    def validate_quantity(self, value):
        """
        Validate quantity is positive
        """
        if value <= 0:
            raise serializers.ValidationError("Quantity must be greater than 0.")
        return value

    def validate(self, attrs):
        """
        Validate stock availability for the product
        """
        product = attrs.get('product')
        quantity = attrs.get('quantity')

        # For updates, get the product from instance if not in attrs
        if not product and self.instance:
            product = self.instance.product

        if not product:
            raise serializers.ValidationError("Product is required.")

        # Check if product is active
        if not product.is_active:
            raise serializers.ValidationError(
                f"Product '{product.name}' is currently unavailable."
            )

        # Check stock availability
        if product.stock_quantity < quantity:
            raise serializers.ValidationError(
                f"Only {product.stock_quantity} units of '{product.name}' are available in stock."
            )

        # For updates, consider the existing quantity in cart
        if self.instance and self.instance.product == product:
            # If updating the same product, we need to check against total quantity
            other_quantity = self.instance.quantity
            if product.stock_quantity < quantity:
                raise serializers.ValidationError(
                    f"Only {product.stock_quantity} units available. You currently have {other_quantity} in cart."
                )

        return attrs

    def create(self, validated_data):
        """
        Create cart item or update quantity if already exists
        """
        cart = validated_data.get('cart')
        product = validated_data.get('product')
        quantity = validated_data.get('quantity')

        # Check if item already exists in cart
        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            defaults={'quantity': quantity}
        )

        if not created:
            # Item exists, update quantity
            cart_item.quantity += quantity
            # Validate stock again with new quantity
            if cart_item.quantity > product.stock_quantity:
                raise serializers.ValidationError(
                    f"Cannot add more items. Only {product.stock_quantity} units available."
                )
            cart_item.save()

        return cart_item


class CartSerializer(serializers.ModelSerializer):
    """
    Serializer for Cart with nested items and calculated totals
    """
    items = CartItemSerializer(many=True, read_only=True)
    total_items = serializers.SerializerMethodField()
    subtotal = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = ['id', 'items', 'total_items', 'subtotal', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_total_items(self, obj):
        """
        Calculate total number of items in cart
        """
        return sum(item.quantity for item in obj.items.all())

    def get_subtotal(self, obj):
        """
        Calculate cart subtotal (sum of all item totals)
        """
        return sum(item.product.price * item.quantity for item in obj.items.all())


class AddToCartSerializer(serializers.Serializer):
    """
    Serializer for adding items to cart
    """
    product_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1, default=1)

    def validate_product_id(self, value):
        """
        Validate product exists and is active
        """
        try:
            product = Product.objects.get(id=value)
            if not product.is_active:
                raise serializers.ValidationError("This product is currently unavailable.")
            return value
        except Product.DoesNotExist:
            raise serializers.ValidationError("Product not found.")

    def validate(self, attrs):
        """
        Validate stock availability
        """
        product_id = attrs.get('product_id')
        quantity = attrs.get('quantity')

        try:
            product = Product.objects.get(id=product_id)
            if product.stock_quantity < quantity:
                raise serializers.ValidationError(
                    f"Only {product.stock_quantity} units available in stock."
                )
        except Product.DoesNotExist:
            pass  # Already validated in validate_product_id

        return attrs


class UpdateCartItemSerializer(serializers.Serializer):
    """
    Serializer for updating cart item quantity
    """
    quantity = serializers.IntegerField(min_value=0)

    def validate_quantity(self, value):
        """
        Validate quantity against stock
        """
        cart_item = self.context.get('cart_item')
        if cart_item and value > 0:
            if value > cart_item.product.stock_quantity:
                raise serializers.ValidationError(
                    f"Only {cart_item.product.stock_quantity} units available in stock."
                )
        return value