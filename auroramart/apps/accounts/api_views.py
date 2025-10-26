from rest_framework import generics, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView
from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.views import ObtainAuthToken

from .serializers import (
    UserSerializer,
    UserRegistrationSerializer,
    UserProfileUpdateSerializer,
    ChangePasswordSerializer
)

User = get_user_model()


class UserRegistrationView(generics.CreateAPIView):
    """
    API view for user registration.
    
    POST /api/auth/register/
    
    Body: {
        "username": "johndoe",
        "email": "john@example.com",
        "password": "SecurePass123!",
        "password_confirm": "SecurePass123!",
        "first_name": "John",
        "last_name": "Doe",
        "phone": "1234567890",
        "age": 25,
        "gender": "male"
    }
    
    Phase 3: Just create user and return token
    Phase 10: Trigger ML category prediction after registration
    """
    serializer_class = UserRegistrationSerializer
    permission_classes = [AllowAny]

    def perform_create(self, serializer):
        """
        Create user and handle post-registration logic
        """
        user = serializer.save()
        
        # =============================================================================
        # ML INTEGRATION POINT - Phase 10
        # Current: Just creating user
        # TODO Phase 10: Trigger ML category prediction
        # - Analyze user demographics (age, gender)
        # - Predict preferred categories using ML model
        # - Store predictions for personalized recommendations
        # =============================================================================
        # Phase 10: trigger_category_prediction(user)
        
        return user

    def create(self, request, *args, **kwargs):
        """
        Create user and return user data with token
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = self.perform_create(serializer)
        
        # Create token for the user
        token, created = Token.objects.get_or_create(user=user)
        
        # Return user data with token
        user_serializer = UserSerializer(user, context={'request': request})
        
        return Response(
            {
                'message': 'User registered successfully',
                'user': user_serializer.data,
                'token': token.key
            },
            status=status.HTTP_201_CREATED
        )


class UserLoginView(ObtainAuthToken):
    """
    API view for user login.
    
    POST /api/auth/login/
    
    Body: {
        "username": "johndoe",
        "password": "SecurePass123!"
    }
    
    Returns user data and authentication token.
    """
    
    def post(self, request, *args, **kwargs):
        """
        Authenticate user and return token with user data
        """
        serializer = self.serializer_class(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        token, created = Token.objects.get_or_create(user=user)
        
        user_serializer = UserSerializer(user, context={'request': request})
        
        return Response({
            'message': 'Login successful',
            'user': user_serializer.data,
            'token': token.key
        })


class UserLogoutView(APIView):
    """
    API view for user logout.
    
    POST /api/auth/logout/
    
    Deletes the user's authentication token.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        Delete user's token to log them out
        """
        try:
            # Delete the user's token
            request.user.auth_token.delete()
            return Response(
                {'message': 'Logged out successfully'},
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {'error': 'Something went wrong'},
                status=status.HTTP_400_BAD_REQUEST
            )


class UserProfileView(generics.RetrieveUpdateAPIView):
    """
    API view for viewing and updating user profile.
    
    GET /api/auth/profile/ - Get current user profile
    PATCH /api/auth/profile/ - Update current user profile
    PUT /api/auth/profile/ - Full update of current user profile
    
    Requires authentication.
    """
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        """
        Return the current authenticated user
        """
        return self.request.user

    def get_serializer_class(self):
        """
        Use different serializers for GET vs PATCH/PUT
        """
        if self.request.method == 'GET':
            return UserSerializer
        return UserProfileUpdateSerializer


class ChangePasswordView(APIView):
    """
    API view for changing user password.
    
    POST /api/auth/change-password/
    
    Body: {
        "old_password": "OldPass123!",
        "new_password": "NewPass123!",
        "new_password_confirm": "NewPass123!"
    }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        Change user's password
        """
        serializer = ChangePasswordSerializer(
            data=request.data,
            context={'request': request}
        )
        
        if serializer.is_valid():
            serializer.save()
            return Response(
                {'message': 'Password changed successfully'},
                status=status.HTTP_200_OK
            )
        
        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )


class UserDeleteView(APIView):
    """
    API view for deleting user account.
    
    DELETE /api/auth/delete-account/
    
    Body: {
        "password": "CurrentPass123!"
    }
    
    Requires password confirmation for security.
    """
    permission_classes = [IsAuthenticated]

    def delete(self, request):
        """
        Delete user account after password confirmation
        """
        user = request.user
        password = request.data.get('password')
        
        if not password:
            return Response(
                {'error': 'Password is required to delete account'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Verify password
        if not user.check_password(password):
            return Response(
                {'error': 'Incorrect password'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Delete user
        username = user.username
        user.delete()
        
        return Response(
            {'message': f'Account {username} deleted successfully'},
            status=status.HTTP_200_OK
        )


class UserStatsView(APIView):
    """
    API view for user statistics.
    
    GET /api/auth/stats/
    
    Returns user's order statistics and activity data.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Get user statistics
        """
        user = request.user
        
        # Get order statistics
        from apps.orders.models import Order
        orders = Order.objects.filter(user=user)
        
        total_orders = orders.count()
        total_spent = sum(order.total for order in orders)
        
        # Order status breakdown
        status_counts = {}
        for order in orders:
            status_counts[order.status] = status_counts.get(order.status, 0) + 1
        
        # Get cart information
        from apps.cart.models import Cart
        try:
            cart = Cart.objects.get(user=user)
            cart_items_count = sum(item.quantity for item in cart.items.all())
            cart_total = sum(
                item.product.price * item.quantity 
                for item in cart.items.all()
            )
        except Cart.DoesNotExist:
            cart_items_count = 0
            cart_total = 0
        
        return Response({
            'user': {
                'username': user.username,
                'email': user.email,
                'date_joined': user.date_joined,
                'last_login': user.last_login
            },
            'orders': {
                'total_orders': total_orders,
                'total_spent': float(total_spent),
                'orders_by_status': status_counts
            },
            'cart': {
                'items_count': cart_items_count,
                'cart_total': float(cart_total)
            }
        })