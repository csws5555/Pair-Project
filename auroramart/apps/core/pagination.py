from rest_framework.pagination import PageNumberPagination


class StandardResultsSetPagination(PageNumberPagination):
    """
    Standard pagination class for most list views.
    
    Default: 20 items per page
    Max: 100 items per page
    """
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class ProductListPagination(PageNumberPagination):
    """
    Pagination class specifically for product listings.
    
    Default: 20 items per page
    Max: 50 items per page
    """
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 50


class OrderListPagination(PageNumberPagination):
    """
    Pagination class for order listings.
    
    Default: 10 items per page
    Max: 50 items per page
    """
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 50