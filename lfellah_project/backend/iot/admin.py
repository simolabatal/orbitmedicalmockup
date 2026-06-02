from django.contrib import admin
from .models import Device, SensorReading, PumpCommand, DeviceConfig, SensorData


class DeviceConfigInline(admin.StackedInline):
    model = DeviceConfig
    can_delete = False
    fields = ('ssid', 'password', 'use_deep_sleep', 'sleep_duration', 'use_flash', 'lang')


@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = ('name', 'device_type', 'owner', 'status', 'mac_address', 'last_seen', 'is_active')
    list_filter = ('device_type', 'status', 'is_active')
    search_fields = ('name', 'mac_address', 'device_token', 'owner__email')
    readonly_fields = ('device_token', 'last_seen')
    inlines = [DeviceConfigInline]


@admin.register(SensorReading)
class SensorReadingAdmin(admin.ModelAdmin):
    list_display = ('device', 'sensor_type', 'value', 'unit', 'recorded_at')
    list_filter = ('sensor_type', 'recorded_at')
    search_fields = ('device__name',)
    readonly_fields = ('recorded_at',)
    date_hierarchy = 'recorded_at'


@admin.register(PumpCommand)
class PumpCommandAdmin(admin.ModelAdmin):
    list_display = ('device', 'command', 'status', 'created_by', 'created_at')
    list_filter = ('command', 'status')
    readonly_fields = ('created_at', 'executed_at')


@admin.register(SensorData)
class SensorDataAdmin(admin.ModelAdmin):
    list_display = ('device', 'temperature', 'humidity', 'tds', 'ph', 'recorded_at')
    list_filter = ('device', 'recorded_at')
    search_fields = ('device__name',)
    readonly_fields = ('recorded_at',)
    date_hierarchy = 'recorded_at'
    fieldsets = (
        ('Capteurs', {'fields': ('device', 'temperature', 'humidity', 'tds', 'ph')}),
        ('Horodatage', {'fields': ('recorded_at',)}),
    )
