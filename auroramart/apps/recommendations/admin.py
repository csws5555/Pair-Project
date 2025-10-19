from django.contrib import admin
from .models import UserBrowsingHistory, ProductRecommendation, CategoryRecommendation


@admin.register(UserBrowsingHistory)
class UserBrowsingHistoryAdmin(admin.ModelAdmin):
    list_display = [
        'user',
        'product',
        'category',
        'viewed_at',
        'session_id'
    ]
    list_filter = [
        'viewed_at',
        'category',
        ('user', admin.EmptyFieldListFilter),
    ]
    search_fields = [
        'user__username',
        'user__email',
        'product__name',
        'category__name',
        'session_id'
    ]
    readonly_fields = [
        'user',
        'product',
        'category',
        'viewed_at',
        'session_id'
    ]
    date_hierarchy = 'viewed_at'
    
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ProductRecommendation)
class ProductRecommendationAdmin(admin.ModelAdmin):
    list_display = [
        'product',
        'recommended_product',
        'recommendation_type',
        'score',
        'generated_at'
    ]
    list_filter = [
        'recommendation_type',
        'generated_at',
    ]
    search_fields = [
        'product__name',
        'recommended_product__name',
    ]
    readonly_fields = [
        'product',
        'recommended_product',
        'recommendation_type',
        'score',
        'generated_at'
    ]
    date_hierarchy = 'generated_at'
    
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(CategoryRecommendation)
class CategoryRecommendationAdmin(admin.ModelAdmin):
    list_display = [
        'user',
        'category',
        'prediction_score',
        'predicted_at'
    ]
    list_filter = [
        'predicted_at',
        'category',
    ]
    search_fields = [
        'user__username',
        'user__email',
        'category__name',
    ]
    readonly_fields = [
        'user',
        'category',
        'prediction_score',
        'predicted_at'
    ]
    date_hierarchy = 'predicted_at'
    
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False