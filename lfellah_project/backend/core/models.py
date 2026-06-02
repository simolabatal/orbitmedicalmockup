from django.db import models
from django.conf import settings


class PlantScan(models.Model):
    SEVERITY_CHOICES = [
        ('healthy', 'Sain'),
        ('warning', 'Attention'),
        ('critical', 'Critique'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='plant_scans',
    )
    image = models.ImageField(upload_to='plant_scans/')
    disease_name = models.CharField(max_length=255, blank=True)
    confidence = models.FloatField(default=0.0)
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, default='warning')
    watering_advice = models.TextField(blank=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    temperature_c = models.FloatField(null=True, blank=True)
    humidity_pct = models.FloatField(null=True, blank=True)
    weather_condition = models.CharField(max_length=100, blank=True)
    is_archived = models.BooleanField(default=False)
    device = models.ForeignKey('iot.Device', on_delete=models.SET_NULL, null=True, blank=True, related_name='scans')
    scanned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-scanned_at']
        indexes = [
            models.Index(fields=['-scanned_at']),
            models.Index(fields=['severity']),
        ]

    def __str__(self):
        return f"Scan #{self.id} - {self.disease_name or 'Analyse en cours'}"


class SystemNotification(models.Model):
    TYPE_CHOICES = [
        ('info', 'Information'),
        ('warning', 'Alerte'),
        ('error', 'Erreur'),
    ]
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='info')
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.type.upper()}] {self.message[:80]}"


class Alert(models.Model):
    ALERT_TYPES = [
        ('critical_disease', 'Maladie Critique'),
        ('high_confidence', 'Haute Confiance'),
        ('spread_risk', 'Risque de Propagation'),
        ('device_offline', 'Appareil Hors-Ligne'),
    ]
    scan = models.ForeignKey(PlantScan, on_delete=models.CASCADE, null=True, blank=True, related_name='alerts')
    alert_type = models.CharField(max_length=30, choices=ALERT_TYPES)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [models.Index(fields=['is_read', '-created_at'])]

    def __str__(self):
        return f"[{self.alert_type}] {self.message[:80]}"


class SecurityLog(models.Model):
    ip_address = models.GenericIPAddressField()
    endpoint = models.CharField(max_length=500)
    method = models.CharField(max_length=10)
    status_code = models.IntegerField(default=200)
    failed_attempts = models.IntegerField(default=0)
    is_blocked = models.BooleanField(default=False)
    user_agent = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['ip_address', '-timestamp']),
            models.Index(fields=['is_blocked']),
        ]

    def __str__(self):
        return f"{self.ip_address} -> {self.endpoint} [{self.status_code}]"


class BlockedIP(models.Model):
    ip_address = models.GenericIPAddressField(unique=True)
    reason = models.TextField()
    blocked_at = models.DateTimeField(auto_now_add=True)
    blocked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='blocked_ips',
    )

    def __str__(self):
        return f"BLOCKED: {self.ip_address}"


class ChatMessage(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='chat_messages',
    )
    session_id = models.CharField(max_length=100, db_index=True)
    role = models.CharField(max_length=10, choices=[('user', 'User'), ('bot', 'Bot')])
    message = models.TextField()
    language = models.CharField(max_length=5, default='fr')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']


class Report(models.Model):
    generated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reports',
    )
    week_start = models.DateField()
    week_end = models.DateField()
    pdf_file = models.FileField(upload_to='reports/', null=True, blank=True)
    total_scans = models.IntegerField(default=0)
    critical_count = models.IntegerField(default=0)
    warning_count = models.IntegerField(default=0)
    healthy_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-week_start']

    def __str__(self):
        return f"Rapport {self.week_start} -> {self.week_end}"
