from django.db import models
from django.core.validators import MinValueValidator
from django.contrib.auth.models import User


class Payment(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='payments'
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0.01)]
    )
    status = models.CharField(  # Замість TextField
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    external_id = models.CharField(max_length=255, default='unknown')
    user_email = models.EmailField(max_length=255, default='unknown')
    created_at = models.DateTimeField(auto_now_add=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Payment #{self.id} by {self.user.username} — {self.amount} ({self.status})"


# Можна винести в constants.py
LANGUAGE_CHOICES = [
    ('en', 'English'),
    ('uk', 'Ukrainian'),
    ('pl', 'Polish'),
    ('de', 'German'),
    ('fr', 'French'),
]


class Translation(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='translations'
    )
    payment = models.ForeignKey(
        Payment,
        on_delete=models.CASCADE,
        related_name='translations',
        null=True,
        blank=True
    )
    source_text = models.TextField()
    translated_text = models.TextField()
    source_lang = models.CharField(max_length=10, choices=LANGUAGE_CHOICES)
    target_lang = models.CharField(max_length=10, choices=LANGUAGE_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.source_lang}->{self.target_lang}: {self.source_text[:30]}..."


class PendingTranslation(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    text = models.TextField()
    source_lang = models.CharField(max_length=5)
    target_lang = models.CharField(max_length=5)
    order_reference = models.CharField(max_length=100, unique=True)
