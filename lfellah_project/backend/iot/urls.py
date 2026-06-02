from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'devices', views.DeviceViewSet, basename='devices')
router.register(r'sensor-readings', views.SensorReadingViewSet, basename='sensor-readings')
router.register(r'pump-commands', views.PumpCommandViewSet, basename='pump-commands')

urlpatterns = [
    path('api/iot/', include(router.urls)),
    path('api/iot/sensor-data/', views.sensor_data_ingest, name='sensor-data-ingest'),
    path('api/iot/sensor-data/v2/', views.sensor_data_ingest_v2, name='sensor-data-ingest-v2'),
    path('api/iot/sensor-data/list/', views.sensor_data_api, name='sensor-data-list'),
    path('api/iot/sensor-data/chart/', views.sensor_data_chart_api, name='sensor-data-chart'),
    path('api/iot/sensor-data/latest/', views.latest_sensor_data, name='sensor-data-latest'),
    path('api/iot/pump-control/', views.pump_control, name='pump-control'),
    path('api/iot/devices/<int:device_id>/pump-status/', views.device_pump_status, name='device-pump-status'),
    path('api/iot/pending-commands/<str:device_token>/', views.device_pending_commands, name='device-pending-commands'),

    # Dashboard capteurs HTML
    path('dashboard-capteurs/', views.sensor_dashboard_page, name='sensor-dashboard'),
]
