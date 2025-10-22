from django.apps import AppConfig
from django.db import models
from django.contrib.auth import get_user_model


class ProductsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.products'

    def ready(self):
        """Import signals when app is ready"""
        # Import signals here if you have any
        # import apps.products.signals
        pass


