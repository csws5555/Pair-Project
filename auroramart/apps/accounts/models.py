from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    USER_TYPE_CHOICES = [
        ('customer', 'Customer'),
        ('admin', 'Admin'),
    ]

    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
        ('N', 'Prefer not to say'),
    ]

    INCOME_CHOICES = [
        ('LOW', 'Less than $25,000'),
        ('LOWER_MIDDLE', '$25,000 - $49,999'),
        ('MIDDLE', '$50,000 - $74,999'),
        ('UPPER_MIDDLE', '$75,000 - $99,999'),
        ('HIGH', '$100,000 - $149,999'),
        ('VERY_HIGH', '$150,000+'),
    ]

    EMPLOYMENT_CHOICES = [
        ('EMPLOYED_FULL', 'Employed Full-Time'),
        ('EMPLOYED_PART', 'Employed Part-Time'),
        ('SELF_EMPLOYED', 'Self-Employed'),
        ('UNEMPLOYED', 'Unemployed'),
        ('STUDENT', 'Student'),
        ('RETIRED', 'Retired'),
    ]

    user_type = models.CharField(max_length=20, choices=USER_TYPE_CHOICES, default='customer')
    phone_number = models.CharField(max_length=15, blank=True, null=True)

    # Demographics for ML
    age = models.IntegerField(blank=True, null=True)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, blank=True, null=True)
    employment_status = models.CharField(max_length=50, choices=EMPLOYMENT_CHOICES, blank=True, null=True)
    income_level = models.CharField(max_length=50, choices=INCOME_CHOICES, blank=True, null=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    predicted_category = models.ForeignKey(
        'products.Category',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='predicted_users',
        help_text='ML-predicted preferred category for personalization'
    )
    
    class Meta:
        db_table = 'users'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.username
    
    @property
    def is_admin(self):
        return self.user_type == 'admin'
    
    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip() or self.username