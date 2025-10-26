from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import status

from apps.products.models import Product
from apps.cart.models import Cart
from apps.products.serializers import ProductListSerializer
from .recommendation_utils import (
    get_category_prediction_fallback,
    get_frequently_bought_together_fallback,
    get_cart_recommendations_fallback,
    get_contextual_recommendations_fallback
)


# =============================================================================
# ML INTEGRATION POINT - Phase 10
# Current: Using fallback recommendation functions
# TODO Phase 10: Replace with ML service calls
# =============================================================================

class CategoryPredictionView(APIView):
    """
    Get predicted category for the authenticated user.
    
    Phase 3: Uses cached prediction or popular category
    Phase 10: Will use ML prediction model
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        prediction = get_category_prediction_fallback(request.user)
        
        return Response({
            'predicted_category': prediction,
            'source': 'fallback',  # Phase 10: change to 'ml'
            'message': 'Using cached prediction' if prediction else 'No prediction available'
        })


class ProductRecommendationsView(APIView):
    """
    Get "Frequently Bought Together" recommendations for a product.
    
    Phase 3: Returns products from same category
    Phase 10: Will use ML association rules
    """
    
    def get(self, request):
        product_id = request.query_params.get('product_id')
        
        if not product_id:
            return Response(
                {'error': 'product_id required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            product = Product.objects.get(id=product_id)
            recommendations = get_frequently_bought_together_fallback(product)
            
            serializer = ProductListSerializer(recommendations, many=True)
            return Response({
                'products': serializer.data,
                'recommendation_type': 'frequently_bought_together',
                'source': 'fallback'  # Phase 10: change to 'ml'
            })
        except Product.DoesNotExist:
            return Response(
                {'error': 'Product not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )


class CartRecommendationsView(APIView):
    """
    Get recommendations based on current cart items.
    
    Phase 3: Returns complementary products from cart categories
    Phase 10: Will use ML cart recommendations
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        cart, created = Cart.objects.get_or_create(user=request.user)
        cart_items = cart.items.all()
        
        if not cart_items.exists():
            return Response({
                'products': [],
                'message': 'Add items to cart for recommendations'
            })
        
        recommendations = get_cart_recommendations_fallback(cart_items)
        
        serializer = ProductListSerializer(recommendations, many=True)
        return Response({
            'products': serializer.data,
            'recommendation_type': 'cart_recommendations',
            'source': 'fallback'  # Phase 10: change to 'ml'
        })


class ContextualRecommendationsView(APIView):
    """
    Get contextual recommendations based on browsing history.
    
    Phase 3: Returns trending or category-based products
    Phase 10: Will use ML contextual recommendations
    """
    
    def get(self, request):
        # Get recently viewed products from session
        viewed_products = request.session.get('viewed_products', [])[-10:]
        
        recommendations = get_contextual_recommendations_fallback(viewed_products)
        
        serializer = ProductListSerializer(recommendations, many=True)
        return Response({
            'products': serializer.data,
            'recommendation_type': 'contextual',
            'source': 'fallback',  # Phase 10: change to 'ml'
            'based_on_views': len(viewed_products) > 0
        })