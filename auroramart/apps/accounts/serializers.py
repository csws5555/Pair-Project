from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """
    Serializer for User model (read-only for profile viewing)
    """
    full_name = serializers.SerializerMethodField()
    age_display = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'full_name', 'phone', 'age', 'age_display', 'gender',
            'date_joined', 'last_login'
        ]
        read_only_fields = [
            'id', 'username', 'date_joined', 'last_login'
        ]

    def get_full_name(self, obj):
        """
        Get user's full name
        """
        if obj.first_name and obj.last_name:
            return f"{obj.first_name} {obj.last_name}"
        return obj.username

    def get_age_display(self, obj):
        """
        Get formatted age display
        """
        if obj.age:
            return f"{obj.age} years old"
        return "Not specified"


class UserRegistrationSerializer(serializers.ModelSerializer):
    """
    Serializer for user registration with password validation
    """
    password = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'}
    )
    password_confirm = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'}
    )
    email = serializers.EmailField(required=True)

    class Meta:
        model = User
        fields = [
            'username', 'email', 'password', 'password_confirm',
            'first_name', 'last_name', 'phone', 'age', 'gender'
        ]
        extra_kwargs = {
            'first_name': {'required': True},
            'last_name': {'required': True},
        }

    def validate_username(self, value):
        """
        Validate username is unique and meets requirements
        """
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError("This username is already taken.")
        
        if len(value) < 3:
            raise serializers.ValidationError("Username must be at least 3 characters long.")
        
        if not value.isalnum() and '_' not in value:
            raise serializers.ValidationError(
                "Username can only contain letters, numbers, and underscores."
            )
        
        return value.lower()

    def validate_email(self, value):
        """
        Validate email is unique
        """
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("This email address is already registered.")
        return value.lower()

    def validate_phone(self, value):
        """
        Validate phone number format
        """
        if value:
            # Remove common separators
            cleaned_phone = ''.join(filter(str.isdigit, value))
            if len(cleaned_phone) < 10:
                raise serializers.ValidationError(
                    "Phone number must be at least 10 digits."
                )
            return cleaned_phone
        return value

    def validate_age(self, value):
        """
        Validate age is within reasonable range
        """
        if value is not None:
            if value < 13:
                raise serializers.ValidationError("You must be at least 13 years old to register.")
            if value > 120:
                raise serializers.ValidationError("Please enter a valid age.")
        return value

    def validate_password(self, value):
        """
        Validate password using Django's password validators
        """
        try:
            validate_password(value)
        except DjangoValidationError as e:
            raise serializers.ValidationError(list(e.messages))
        return value

    def validate(self, attrs):
        """
        Validate password confirmation matches
        """
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({
                'password_confirm': "Passwords do not match."
            })
        return attrs

    def create(self, validated_data):
        """
        Create user with hashed password
        """
        # Remove password_confirm as it's not a model field
        validated_data.pop('password_confirm')
        
        # Extract password
        password = validated_data.pop('password')
        
        # Create user instance
        user = User(**validated_data)
        user.set_password(password)  # Hash the password
        user.save()
        
        return user


class UserProfileUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating user profile (excluding sensitive fields)
    """
    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'phone', 'age', 'gender'
        ]

    def validate_phone(self, value):
        """
        Validate phone number format
        """
        if value:
            cleaned_phone = ''.join(filter(str.isdigit, value))
            if len(cleaned_phone) < 10:
                raise serializers.ValidationError(
                    "Phone number must be at least 10 digits."
                )
            return cleaned_phone
        return value

    def validate_age(self, value):
        """
        Validate age is within reasonable range
        """
        if value is not None:
            if value < 13:
                raise serializers.ValidationError("Age must be at least 13.")
            if value > 120:
                raise serializers.ValidationError("Please enter a valid age.")
        return value


class ChangePasswordSerializer(serializers.Serializer):
    """
    Serializer for password change
    """
    old_password = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'}
    )
    new_password = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'}
    )
    new_password_confirm = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'}
    )

    def validate_old_password(self, value):
        """
        Validate old password is correct
        """
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Current password is incorrect.")
        return value

    def validate_new_password(self, value):
        """
        Validate new password using Django's password validators
        """
        try:
            validate_password(value, user=self.context['request'].user)
        except DjangoValidationError as e:
            raise serializers.ValidationError(list(e.messages))
        return value

    def validate(self, attrs):
        """
        Validate new passwords match and are different from old
        """
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError({
                'new_password_confirm': "New passwords do not match."
            })
        
        if attrs['old_password'] == attrs['new_password']:
            raise serializers.ValidationError({
                'new_password': "New password must be different from current password."
            })
        
        return attrs

    def save(self):
        """
        Update user password
        """
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.save()
        return user


class PasswordResetRequestSerializer(serializers.Serializer):
    """
    Serializer for password reset request
    """
    email = serializers.EmailField(required=True)

    def validate_email(self, value):
        """
        Validate email exists (but don't reveal if it doesn't for security)
        """
        return value.lower()


class PasswordResetConfirmSerializer(serializers.Serializer):
    """
    Serializer for password reset confirmation
    """
    new_password = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'}
    )
    new_password_confirm = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'}
    )

    def validate_new_password(self, value):
        """
        Validate new password
        """
        try:
            validate_password(value)
        except DjangoValidationError as e:
            raise serializers.ValidationError(list(e.messages))
        return value

    def validate(self, attrs):
        """
        Validate passwords match
        """
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError({
                'new_password_confirm': "Passwords do not match."
            })
        return attrs