from django.db import models
from django.conf import settings
from apps.products.models import Product, Category


class UserBrowsingHistory(models.Model):
    """Track user browsing behavior for recommendation engine"""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='browsing_history'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='views'
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name='browsing_history'
    )
    viewed_at = models.DateTimeField(auto_now_add=True)
    session_id = models.CharField(
        max_length=255,
        blank=True,
        help_text="Session ID for anonymous users"
    )

    class Meta:
        ordering = ['-viewed_at']
        indexes = [
            models.Index(fields=['user', '-viewed_at']),
            models.Index(fields=['session_id', '-viewed_at']),
            models.Index(fields=['product', '-viewed_at']),
        ]
        verbose_name = "User Browsing History"
        verbose_name_plural = "User Browsing Histories"

    def __str__(self):
        user_identifier = self.user.username if self.user else f"Session: {self.session_id}"
        return f"{user_identifier} viewed {self.product.name} at {self.viewed_at}"


class ProductRecommendation(models.Model):
    """Cache product-to-product recommendations"""
    RECOMMENDATION_TYPES = [
        ('frequently_bought', 'Frequently Bought Together'),
        ('similar', 'Similar Products'),
        ('contextual', 'Contextual Recommendations'),
    ]

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='source_recommendations',
        help_text="The product for which recommendations are made"
    )
    recommended_product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='target_recommendations',
        help_text="The recommended product"
    )
    recommendation_type = models.CharField(
        max_length=20,
        choices=RECOMMENDATION_TYPES
    )
    score = models.FloatField(
        help_text="Recommendation confidence score (0-1)"
    )
    generated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [['product', 'recommended_product', 'recommendation_type']]
        indexes = [
            models.Index(fields=['product', 'recommendation_type', '-score']),
            models.Index(fields=['-generated_at']),
        ]
        verbose_name = "Product Recommendation"
        verbose_name_plural = "Product Recommendations"

    def __str__(self):
        return f"{self.product.name} -> {self.recommended_product.name} ({self.get_recommendation_type_display()})"


class CategoryRecommendation(models.Model):
    """Cache user-specific category predictions"""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='category_predictions'
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name='user_predictions'
    )
    prediction_score = models.FloatField(
        help_text="Predicted interest score (0-1)"
    )
    predicted_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['user', '-prediction_score']),
            models.Index(fields=['-predicted_at']),
        ]
        verbose_name = "Category Recommendation"
        verbose_name_plural = "Category Recommendations"

    def __str__(self):
        return f"{self.user.username} -> {self.category.name} (Score: {self.prediction_score:.2f})"