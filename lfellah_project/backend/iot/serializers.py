from rest_framework import serializers
from .models import Device, SensorReading, PumpCommand, DeviceConfig, SensorData


class DeviceConfigWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeviceConfig
        fields = [
            'ssid', 'password', 'use_deep_sleep',
            'sleep_duration', 'use_flash', 'lang',
        ]
        extra_kwargs = {
            'password': {'write_only': True},
        }


class DeviceConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeviceConfig
        fields = [
            'ssid', 'use_deep_sleep',
            'sleep_duration', 'use_flash', 'lang',
        ]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['has_password'] = bool(instance.password)
        return data


class DeviceSerializer(serializers.ModelSerializer):
    owner_email = serializers.EmailField(source='owner.email', read_only=True)
    config = DeviceConfigSerializer(read_only=True)
    last_sensor_readings = serializers.SerializerMethodField()

    class Meta:
        model = Device
        fields = [
            'id', 'owner', 'owner_email', 'device_type', 'name',
            'mac_address', 'device_token', 'status',
            'firmware_version', 'latitude', 'longitude',
            'last_seen', 'is_active', 'config',
            'last_sensor_readings', 'created_at', 'updated_at',
        ]
        read_only_fields = ['device_token', 'status', 'last_seen', 'created_at', 'updated_at']

    def get_last_sensor_readings(self, obj):
        # Dernière lecture de chaque type de capteur
        readings = {}
        latest = obj.sensor_readings.order_by('sensor_type', '-recorded_at').distinct('sensor_type')
        for r in latest:
            readings[r.sensor_type] = SensorReadingSerializer(r).data
        return readings


class SensorReadingSerializer(serializers.ModelSerializer):
    device_name = serializers.CharField(source='device.name', read_only=True)

    class Meta:
        model = SensorReading
        fields = [
            'id', 'device', 'device_name', 'sensor_type',
            'value', 'unit', 'recorded_at',
        ]
        read_only_fields = ['recorded_at']


class SensorReadingCreateSerializer(serializers.Serializer):
    """Pour l'ESP32 qui envoie des données brutes (JSON)"""
    device_token = serializers.CharField(max_length=128)
    sensor_type = serializers.ChoiceField(choices=SensorReading.SENSOR_TYPES)
    value = serializers.FloatField()
    unit = serializers.CharField(max_length=20, required=False, default='')


class PumpCommandSerializer(serializers.ModelSerializer):
    device_name = serializers.CharField(source='device.name', read_only=True)
    created_by_email = serializers.EmailField(source='created_by.email', read_only=True)

    class Meta:
        model = PumpCommand
        fields = [
            'id', 'device', 'device_name', 'command',
            'duration_seconds', 'scheduled_at', 'status',
            'executed_at', 'created_by', 'created_by_email',
            'created_at',
        ]
        read_only_fields = ['status', 'executed_at', 'created_at', 'created_by']


class PumpControlSerializer(serializers.Serializer):
    """Pour le dashboard: commander la pompe ON/OFF"""
    device_id = serializers.IntegerField()
    command = serializers.ChoiceField(choices=['on', 'off'])
    duration_seconds = serializers.IntegerField(required=False, default=0)


class SensorDataSerializer(serializers.ModelSerializer):
    device_name = serializers.CharField(source='device.name', read_only=True)

    class Meta:
        model = SensorData
        fields = ['id', 'device', 'device_name', 'temperature', 'humidity', 'tds', 'ph', 'recorded_at']
        read_only_fields = ['recorded_at']


class SensorDataCreateSerializer(serializers.Serializer):
    """Reception de donnees depuis l'Arduino (JSON brut)"""
    device_token = serializers.CharField(max_length=128)
    temperature = serializers.FloatField(required=False)
    humidity = serializers.FloatField(required=False)
    tds = serializers.FloatField(required=False)
    ph = serializers.FloatField(required=False)
