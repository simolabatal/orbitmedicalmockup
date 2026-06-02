from rest_framework import serializers
from .models import (
    PlantScan, SystemNotification, Alert, SecurityLog,
    BlockedIP, ChatMessage, Report,
)


class PlantScanSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    device_name = serializers.CharField(source='device.name', read_only=True)

    class Meta:
        model = PlantScan
        fields = [
            'id', 'user', 'user_email', 'device', 'device_name',
            'image', 'disease_name', 'confidence', 'severity',
            'watering_advice', 'latitude', 'longitude',
            'temperature_c', 'humidity_pct', 'weather_condition',
            'is_archived', 'scanned_at',
        ]
        read_only_fields = ['disease_name', 'confidence', 'severity', 'watering_advice', 'scanned_at']


class PlantScanListSerializer(serializers.ModelSerializer):
    """Version allégée pour les listes (sans image en base64)"""

    class Meta:
        model = PlantScan
        fields = [
            'id', 'disease_name', 'confidence', 'severity',
            'is_archived', 'scanned_at', 'image',
        ]


class AlertSerializer(serializers.ModelSerializer):
    class Meta:
        model = Alert
        fields = '__all__'
        read_only_fields = ['created_at']


class SystemNotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = SystemNotification
        fields = '__all__'
        read_only_fields = ['created_at']


class SecurityLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = SecurityLog
        fields = '__all__'
        read_only_fields = ['timestamp']


class BlockedIPSerializer(serializers.ModelSerializer):
    blocked_by_email = serializers.EmailField(source='blocked_by.email', read_only=True)

    class Meta:
        model = BlockedIP
        fields = ['id', 'ip_address', 'reason', 'blocked_at', 'blocked_by', 'blocked_by_email']
        read_only_fields = ['blocked_at', 'blocked_by']


class ChatMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatMessage
        fields = '__all__'
        read_only_fields = ['created_at']


class ReportSerializer(serializers.ModelSerializer):
    pdf_url = serializers.SerializerMethodField()

    class Meta:
        model = Report
        fields = [
            'id', 'week_start', 'week_end', 'total_scans',
            'critical_count', 'warning_count', 'healthy_count',
            'pdf_url', 'created_at',
        ]
        read_only_fields = ['created_at']

    def get_pdf_url(self, obj):
        if obj.pdf_file:
            return self.context.get('request').build_absolute_uri(obj.pdf_file.url)
        return None
