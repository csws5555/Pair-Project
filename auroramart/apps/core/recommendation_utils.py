"""
Recommendation Utilities
Phase 2-9: Simple rule-based fallback recommendations
Phase 10: Enhanced with ML models

This module provides a unified interface for recommendations throughout the app.
Phase 10 will replace the internal logic with ML while keeping the same interface.
"""
from apps.storefront.models import Product, Category
from django.db.models import Count
import logging

logger = logging.getLogger(__name__)

# =============================================================================
# PHASE 10 ML INTEGRATION - These functions will be enhanced with ML
# Current: Using simple rule-based logic
# =============================================================================

def get_category_prediction(user):
    """
    Get category prediction for user

    Phase 2-9: Returns cached prediction or most popular category
    Phase 10: Will call ML model

    Args:
        user: User object

    Returns:
        str: Category name or None
    """
    # Return cached prediction if exists
    if user.predicted_category:
        logger.info(f"Using cached category prediction for user {user.id}: {user.predicted_category}")
        return user.predicted_category

    # Fallback: most popular category
    popular = Category.objects.annotate(
        product_count=Count('products')
    ).filter(is_active=True).order_by('-product_count').first()

    if popular:
        logger.info(f"Fallback: Recommending most popular category '{popular.name}' for user {user.id}")
        return popular.name

    return None


def get_frequently_bought_together(product, limit=3):
    """
    Get Frequently Bought Together recommendations

    Phase 2-9: Returns related products from same category
    Phase 10: Will use ML association rules

    Args:
        product: Product object
        limit: Number of recommendations

    Returns:
        QuerySet: Recommended products
    """
    logger.info(f"Getting FBT recommendations for product {product.id} (fallback mode)")

    return Product.objects.filter(
        category=product.category,
        is_active=True
    ).exclude(id=product.id).order_by('-rating', '-review_count')[:limit]


def get_cart_recommendations(cart_items, limit=4):
    """
    Get "Complete the Set" recommendations for cart

    Phase 2-9: Returns complementary products from cart categories
    Phase 10: Will use ML cart recommendations

    Args:
        cart_items: QuerySet of CartItem objects
        limit: Number of recommendations

    Returns:
        QuerySet: Recommended products
    """
    if not cart_items.exists():
        logger.info("No cart items, returning empty recommendations")
        return Product.objects.none()

    cart_categories = cart_items.values_list('product__category', flat=True).distinct()
    cart_product_ids = cart_items.values_list('product_id', flat=True)

    logger.info(f"Getting cart recommendations from {len(cart_categories)} categories (fallback mode)")

    return Product.objects.filter(
        category__in=cart_categories,
        is_active=True
    ).exclude(id__in=cart_product_ids).order_by('-rating', '-review_count')[:limit]


def get_contextual_recommendations(viewed_products, limit=6):
    """
    Get contextual recommendations based on browsing history

    Phase 2-9: Returns trending products or products from viewed categories
    Phase 10: Will use ML contextual recommendations

    Args:
        viewed_products: List of product IDs
        limit: Number of recommendations

    Returns:
        QuerySet: Recommended products
    """
    if not viewed_products:
        # Return trending products
        logger.info("No browsing history, returning trending products")
        return Product.objects.filter(
            is_active=True
        ).order_by('-rating', '-review_count')[:limit]

    # Get categories from viewed products
    categories = Product.objects.filter(
        id__in=viewed_products
    ).values_list('category', flat=True).distinct()

    logger.info(f"Getting contextual recommendations from {len(categories)} categories (fallback mode)")

    return Product.objects.filter(
        category__in=categories,
        is_active=True
    ).exclude(id__in=viewed_products).order_by('-rating', '-review_count')[:limit]


def get_similar_products(product, limit=6):
    """
    Get similar products based on category and attributes

    Phase 2-9: Returns products from same category
    Phase 10: Will use ML similarity models

    Args:
        product: Product object
        limit: Number of recommendations

    Returns:
        QuerySet: Similar products
    """
    logger.info(f"Getting similar products for product {product.id} (fallback mode)")

    return Product.objects.filter(
        category=product.category,
        is_active=True
    ).exclude(id=product.id).order_by('-rating', '-review_count')[:limit]


def get_personalized_homepage_products(user, limit=8):
    """
    Get personalized product recommendations for homepage

    Phase 2-9: Returns products from predicted category or featured products
    Phase 10: Will use ML personalization

    Args:
        user: User object
        limit: Number of recommendations

    Returns:
        QuerySet: Recommended products
    """
    if user.is_authenticated and user.predicted_category:
        # Show products from predicted category
        try:
            category = Category.objects.get(name=user.predicted_category)
            logger.info(f"Getting personalized products for user {user.id} from category {category.name}")
            return Product.objects.filter(
                category=category,
                is_active=True
            ).order_by('-rating', '-review_count')[:limit]
        except Category.DoesNotExist:
            logger.warning(f"Predicted category '{user.predicted_category}' not found for user {user.id}")

    # Fallback: featured products
    logger.info("Fallback: returning featured products")
    return Product.objects.filter(
        is_featured=True,
        is_active=True
    ).order_by('-rating')[:limit]

