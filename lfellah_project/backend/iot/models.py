from django.db import models
from django.conf import settings


class Device(models.Model):
    DEVICE_TYPES = [
        ('esp32_cam', 'ESP32-CAM'),
        ('esp32_sensor', 'ESP32 Capteur'),
        ('arduino_uno', 'Arduino Uno'),
        ('arduino_mega', 'Arduino Mega'),
    ]
    DEVICE_STATUS = [
        ('online', 'En ligne'),
        ('offline', 'Hors ligne'),
        ('maintenance', 'Maintenance'),
    ]

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='devices',
        db_constraint=False,
        help_text='Contrainte FK desactivee pour compatibilite Multi-DB (MySQL/SQLite)',
    )
    device_type = models.CharField(max_length=30, choices=DEVICE_TYPES)
    name = models.CharField(max_length=100)
    mac_address = models.CharField(max_length=17, unique=True, blank=True, null=True)
    device_token = models.CharField(
        max_length=128,
        unique=True,
        help_text="Token d'authentification pour l'appareil IoT",
    )
    status = models.CharField(max_length=20, choices=DEVICE_STATUS, default='offline')
    firmware_version = models.CharField(max_length=20, blank=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    last_seen = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-last_seen']
        indexes = [
            models.Index(fields=['device_token']),
            models.Index(fields=['status', '-last_seen']),
        ]

    def __str__(self):
        return f"{self.name} ({self.device_type}) - {self.get_status_display()}"


class SensorReading(models.Model):
    SENSOR_TYPES = [
        ('ph', 'pH'),
        ('humidity_soil', 'Humidité Sol'),
        ('temperature_air', 'Température Air'),
        ('temperature_soil', 'Température Sol'),
        ('light', 'Luminosité'),
        ('co2', 'CO2'),
        ('tds', 'TDS (ppm)'),
    ]

    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name='sensor_readings', db_constraint=False)
    sensor_type = models.CharField(max_length=30, choices=SENSOR_TYPES)
    value = models.FloatField()
    unit = models.CharField(max_length=20)
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-recorded_at']
        indexes = [
            models.Index(fields=['device', 'sensor_type', '-recorded_at']),
            models.Index(fields=['-recorded_at']),
        ]

    def __str__(self):
        return f"[{self.device.name}] {self.sensor_type}: {self.value} {self.unit}"


class PumpCommand(models.Model):
    COMMAND_CHOICES = [
        ('on', 'Activer'),
        ('off', 'Désactiver'),
        ('schedule', 'Programmer'),
    ]
    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('sent', 'Envoyée'),
        ('executed', 'Exécutée'),
        ('failed', 'Échouée'),
    ]

    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name='pump_commands', db_constraint=False)
    command = models.CharField(max_length=20, choices=COMMAND_CHOICES)
    duration_seconds = models.PositiveIntegerField(null=True, blank=True, help_text="Durée en secondes si ON")
    scheduled_at = models.DateTimeField(null=True, blank=True, help_text="Planification horaire (schedule)")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    executed_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='pump_commands',
        db_constraint=False,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['device', '-created_at']),
            models.Index(fields=['status']),
            models.Index(fields=['scheduled_at']),
        ]

    def __str__(self):
        return f"[{self.device.name}] POMPE {self.command.upper()}"


class DeviceConfig(models.Model):
    device = models.OneToOneField(Device, on_delete=models.CASCADE, related_name='config', db_constraint=False)
    ssid = models.CharField(max_length=100, blank=True)
    password = models.CharField(max_length=100, blank=True)
    use_deep_sleep = models.BooleanField(default=False)
    sleep_duration = models.PositiveIntegerField(default=300, help_text="Durée veille en secondes")
    use_flash = models.BooleanField(default=False)
    lang = models.CharField(max_length=5, default='fr')
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Config {self.device.name}"


class SensorData(models.Model):
    """
    Donnees multi-capteurs en un seul enregistrement (Arduino Sensor Node).
    Correspond au format JSON envoye par LFellah_Sensor_Node.ino :
      {"temperature": 25.3, "humidity": 68.0, "tds": 450, "ph": 6.8}
    """
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name='sensor_data', db_constraint=False)
    temperature = models.FloatField(null=True, blank=True, help_text='Temperature air (°C)')
    humidity = models.FloatField(null=True, blank=True, help_text='Humidite air (%)')
    tds = models.FloatField(null=True, blank=True, help_text='TDS (ppm)')
    ph = models.FloatField(null=True, blank=True, help_text='pH')
    soil_moisture = models.FloatField(null=True, blank=True, help_text='Humidite sol (%)')
    recorded_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-recorded_at']
        indexes = [
            models.Index(fields=['device', '-recorded_at']),
            models.Index(fields=['-recorded_at']),
        ]
        verbose_name = 'Donnée capteur'
        verbose_name_plural = 'Données capteurs'

    def __str__(self):
        return f"[{self.device.name}] T={self.temperature}°C H={self.humidity}% TDS={self.tds} pH={self.ph}"
