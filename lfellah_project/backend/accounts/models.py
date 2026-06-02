from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings


class User(AbstractUser):
    """
    Modèle utilisateur personnalisé pour L'Fellah 2.0.
    Quatre rôles distincts avec séparation stricte des accès :
      - farmer  : Vendeur/Coopérative (CRUD produits, dashboard vendeur)
      - buyer   : Acheteur B2B (Hôtel/Restaurant, consultation marketplace)
      - marketer: Équipe marketing (KPIs lecture seule, gestion codes promo)
      - admin   : Administrateur système (création comptes SaaS, supervision)
    """
    ROLE_CHOICES = [
        ('farmer', 'Fermier/Coopérative'),
        ('buyer', 'Acheteur (Hôtel/B2B)'),
        ('marketer', 'Marketeur'),
        ('admin', 'Administrateur'),
    ]

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='farmer')
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, blank=True)
    region = models.CharField(max_length=100, blank=True)
    preferred_language = models.CharField(
        max_length=5,
        choices=[('fr', 'Français'), ('ar', 'العربية'), ('en', 'English')],
        default='fr',
    )
    is_blocked = models.BooleanField(default=False)
    force_password_change = models.BooleanField(default=False)
    email_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    class Meta:
        ordering = ['-date_joined']
        indexes = [
            models.Index(fields=['role']),
            models.Index(fields=['is_blocked']),
        ]

    def __str__(self):
        return f"{self.email} ({self.get_role_display()})"

    @property
    def is_farmer(self):
        return self.role == 'farmer'

    @property
    def is_buyer(self):
        return self.role == 'buyer'

    @property
    def is_marketer(self):
        return self.role == 'marketer'

    @property
    def is_saas_staff(self):
        """Retourne True si l'utilisateur est membre du staff SaaS (admin ou créé par admin)."""
        return self.role in ('admin', 'marketer')

    @property
    def is_finance(self):
        """Retourne True si l'utilisateur appartient au groupe Finance."""
        return self.is_authenticated and self.groups.filter(name='Finance').exists()


class PasswordResetToken(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reset_tokens')
    token = models.CharField(max_length=128, unique=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Reset token for {self.user.email} (expires {self.expires_at})"
