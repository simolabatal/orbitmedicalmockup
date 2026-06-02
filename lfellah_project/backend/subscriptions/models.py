from decimal import Decimal
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator


class Plan(models.Model):
    BILLING_CYCLE_CHOICES = [
        ('monthly', 'Mensuel'),
        ('yearly', 'Annuel'),
    ]

    name = models.CharField(max_length=100)
    code = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    billing_cycle = models.CharField(max_length=20, choices=BILLING_CYCLE_CHOICES, default='monthly')
    price_mad = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
    )
    max_devices = models.PositiveIntegerField(default=1)
    max_scans_per_day = models.PositiveIntegerField(default=50)
    max_products = models.PositiveIntegerField(default=10)
    includes_ai_chatbot = models.BooleanField(default=False)
    includes_pdf_reports = models.BooleanField(default=False)
    includes_marketplace = models.BooleanField(default=False)
    includes_iot_control = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['price_mad']

    def __str__(self):
        return f"{self.name} ({self.get_billing_cycle_display()}) - {self.price_mad} MAD"


class Subscription(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('past_due', 'En retard'),
        ('cancelled', 'Annulée'),
        ('expired', 'Expirée'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='subscriptions',
    )
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT, related_name='subscriptions')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    start_date = models.DateTimeField(auto_now_add=True)
    end_date = models.DateTimeField()
    auto_renew = models.BooleanField(default=True)
    payment_method = models.CharField(max_length=50, blank=True)
    last_payment_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['status', 'end_date']),
        ]

    def __str__(self):
        return f"{self.user.email} -> {self.plan.name} ({self.get_status_display()})"

    @property
    def is_active_subscription(self):
        from django.utils import timezone
        return self.status == 'active' and self.end_date > timezone.now()
