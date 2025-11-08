from rest_framework import serializers
from ..models import Category, Product, ProductImage, ProductSpecification


class CategorySerializer(serializers.ModelSerializer):
    """
    Serializer for Category model with nested subcategories
    """
    subcategories = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'description', 'image', 'parent', 'subcategories']
        read_only_fields = ['id', 'slug']

    def get_subcategories(self, obj):
        """
        Get all direct child categories
        """
        if obj.children.exists():
            return CategorySerializer(obj.children.all(), many=True, context=self.context).data
        return []


class ProductImageSerializer(serializers.ModelSerializer):
    """
    Serializer for Product Images
    """
    class Meta:
        model = ProductImage
        fields = ['id', 'image', 'alt_text', 'is_primary', 'order']
        read_only_fields = ['id']

    def validate_order(self, value):
        """
        Validate order is non-negative
        """
        if value < 0:
            raise serializers.ValidationError("Order must be a non-negative integer.")
        return value


class ProductSpecificationSerializer(serializers.ModelSerializer):
    """
    Serializer for Product Specifications
    """
    class Meta:
        model = ProductSpecification
        fields = ['id', 'name', 'value']
        read_only_fields = ['id']

    def validate_name(self, value):
        """
        Validate specification name is not empty
        """
        if not value.strip():
            raise serializers.ValidationError("Specification name cannot be empty.")
        return value.strip()


class ProductListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for product listings
    """
    primary_image = serializers.SerializerMethodField()
    stock_status = serializers.SerializerMethodField()
    category = serializers.StringRelatedField()

    class Meta:
        model = Product
        fields = [
            'id', 'sku', 'name', 'slug', 'price', 'original_price',
            'rating', 'stock_status', 'category', 'primary_image'
        ]
        read_only_fields = ['id', 'slug', 'rating']

    def get_primary_image(self, obj):
        """
        Get the primary product image URL
        """
        primary_image = obj.images.filter(is_primary=True).first()
        if primary_image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(primary_image.image.url)
            return primary_image.image.url
        return None

    def get_stock_status(self, obj):
        """
        Determine stock status based on stock quantity
        """
        if obj.stock_quantity == 0:
            return 'out_of_stock'
        elif obj.stock_quantity <= obj.low_stock_threshold:
            return 'low_stock'
        return 'in_stock'


class ProductDetailSerializer(serializers.ModelSerializer):
    """
    Detailed serializer for single product view
    """
    images = ProductImageSerializer(many=True, read_only=True)
    specifications = ProductSpecificationSerializer(many=True, read_only=True)
    category = CategorySerializer(read_only=True)
    stock_status = serializers.SerializerMethodField()
    discount_percentage = serializers.SerializerMethodField()
    is_available = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            'id', 'sku', 'name', 'slug', 'description', 'price', 'original_price',
            'category', 'stock_quantity', 'low_stock_threshold', 'weight', 'dimensions',
            'rating', 'review_count', 'is_active', 'is_featured', 'created_at',
            'updated_at', 'images', 'specifications', 'stock_status',
            'discount_percentage', 'is_available'
        ]
        read_only_fields = [
            'id', 'slug', 'rating', 'review_count', 'created_at', 'updated_at'
        ]

    def get_stock_status(self, obj):
        """
        Determine stock status based on stock quantity
        """
        if obj.stock_quantity == 0:
            return 'out_of_stock'
        elif obj.stock_quantity <= obj.low_stock_threshold:
            return 'low_stock'
        return 'in_stock'

    def get_discount_percentage(self, obj):
        """
        Calculate discount percentage if original price exists
        """
        if obj.original_price and obj.original_price > obj.price:
            discount = ((obj.original_price - obj.price) / obj.original_price) * 100
            return round(discount, 2)
        return 0

    def get_is_available(self, obj):
        """
        Check if product is available for purchase
        """
        return obj.is_active and obj.stock_quantity > 0