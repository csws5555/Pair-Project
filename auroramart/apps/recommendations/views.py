from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from apps.products.models import Product, Category
from .services import CategoryPredictionService
import logging

logger = logging.getLogger(__name__)


class ProductRecommendationView(APIView):
    """
    API endpoint for product recommendations based on browsing history and ML predictions
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            user = request.user
            limit = int(request.GET.get('limit', 10))

            # Placeholder for ML-based product recommendations
            # TODO: Integrate actual ML model in Phase 4
            recommended_products = Product.objects.filter(
                is_active=True,
                is_featured=True
            )[:limit]

            products_data = [{
                'id': product.id,
                'name': product.name,
                'slug': product.slug,
                'price': str(product.price),
                'category': product.category.name if product.category else None,
            } for product in recommended_products]

            return Response({
                'status': 'success',
                'recommendations': products_data
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error in product recommendations: {e}")
            return Response({
                'status': 'error',
                'message': 'Failed to generate recommendations'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CategoryRecommendationView(APIView):
    """
    API endpoint for recommended category based on user demographics
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            user = request.user
            prediction_service = CategoryPredictionService()

            # Get predicted category
            predicted_category = prediction_service.predict_preferred_category(user)

            if predicted_category:
                return Response({
                    'status': 'success',
                    'category': {
                        'id': predicted_category.id,
                        'name': predicted_category.name,
                        'slug': predicted_category.slug,
                    }
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'status': 'success',
                    'category': None,
                    'message': 'No prediction available'
                }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error in category recommendation: {e}")
            return Response({
                'status': 'error',
                'message': 'Failed to generate category recommendation'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PersonalizedRecommendationView(APIView):
    """
    API endpoint for personalized product recommendations
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            user = request.user
            limit = int(request.GET.get('limit', 10))

            # Get user's predicted category
            prediction_service = CategoryPredictionService()
            predicted_category = prediction_service.predict_preferred_category(user)

            if predicted_category:
                recommended_products = Product.objects.filter(
                    category=predicted_category,
                    is_active=True
                )[:limit]
            else:
                recommended_products = Product.objects.filter(
                    is_active=True,
                    is_featured=True
                )[:limit]

            products_data = [{
                'id': product.id,
                'name': product.name,
                'slug': product.slug,
                'price': str(product.price),
                'category': product.category.name if product.category else None,
            } for product in recommended_products]

            return Response({
                'status': 'success',
                'recommendations': products_data
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error in personalized recommendations: {e}")
            return Response({
                'status': 'error',
                'message': 'Failed to generate personalized recommendations'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CategoryPredictionView(APIView):
    """
    API endpoint for category prediction based on user demographics
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            user = request.user
            prediction_service = CategoryPredictionService()

            # Predict category
            predicted_category = prediction_service.predict_preferred_category(user)

            if predicted_category:
                return Response({
                    'status': 'success',
                    'prediction': {
                        'category_id': predicted_category.id,
                        'category_name': predicted_category.name,
                        'category_slug': predicted_category.slug,
                    }
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'status': 'success',
                    'prediction': None,
                    'message': 'Unable to predict category'
                }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error in category prediction: {e}")
            return Response({
                'status': 'error',
                'message': 'Failed to predict category'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PurchasePredictionView(APIView):
    """
    API endpoint for purchase probability prediction
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            product_id = request.data.get('product_id')

            if not product_id:
                return Response({
                    'status': 'error',
                    'message': 'product_id is required'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Placeholder for ML-based purchase prediction
            # TODO: Integrate actual ML model in Phase 4

            return Response({
                'status': 'success',
                'prediction': {
                    'product_id': product_id,
                    'purchase_probability': 0.5,
                    'confidence': 0.7
                }
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error in purchase prediction: {e}")
            return Response({
                'status': 'error',
                'message': 'Failed to predict purchase probability'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class TrackProductViewView(APIView):
    """
    API endpoint for tracking product views (for ML data collection)
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            product_id = request.data.get('product_id')

            if not product_id:
                return Response({
                    'status': 'error',
                    'message': 'product_id is required'
                }, status=status.HTTP_400_BAD_REQUEST)

            product = get_object_or_404(Product, id=product_id)

            # Track view (placeholder)
            # TODO: Implement actual tracking in Phase 4

            return Response({
                'status': 'success',
                'message': 'View tracked successfully'
            }, status=status.HTTP_200_OK)

        except Product.DoesNotExist:
            return Response({
                'status': 'error',
                'message': 'Product not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error tracking product view: {e}")
            return Response({
                'status': 'error',
                'message': 'Failed to track view'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class TrackClickView(APIView):
    """
    API endpoint for tracking product clicks (for ML data collection)
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            product_id = request.data.get('product_id')
            source = request.data.get('source', 'unknown')

            if not product_id:
                return Response({
                    'status': 'error',
                    'message': 'product_id is required'
                }, status=status.HTTP_400_BAD_REQUEST)

            product = get_object_or_404(Product, id=product_id)

            # Track click (placeholder)
            # TODO: Implement actual tracking in Phase 4

            return Response({
                'status': 'success',
                'message': 'Click tracked successfully'
            }, status=status.HTTP_200_OK)

        except Product.DoesNotExist:
            return Response({
                'status': 'error',
                'message': 'Product not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error tracking click: {e}")
            return Response({
                'status': 'error',
                'message': 'Failed to track click'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
