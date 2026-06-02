from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'scans', views.PlantScanViewSet, basename='scans')
router.register(r'alerts', views.AlertViewSet, basename='alerts')
router.register(r'security-logs', views.SecurityLogViewSet, basename='security-logs')
router.register(r'blocked-ips', views.BlockedIPViewSet, basename='blocked-ips')
router.register(r'reports', views.ReportViewSet, basename='reports')

urlpatterns = [
    path('dashboard-iot/', views.sensor_dashboard, name='sensor-dashboard'),
    path('dashboard-iot/index/', views.sensor_dashboard, name='sensor-dashboard-index'),
    path('dashboard-iot/plant-analysis/', views.sensor_dashboard, name='plant-analysis'),
    path('dashboard-iot/esp32-cam-feed/', views.sensor_dashboard, name='esp32-cam-feed'),
    path('dashboard-admin/', views.dashboard, name='dashboard-iot'),
    path('dashboard-finance/', views.finance_dashboard, name='finance-dashboard'),
    path('dashboard-finance/export-pdf/', views.export_finance_pdf, name='finance-export-pdf'),
    path('dashboard/', views.dashboard_redirect, name='dashboard'),
    path('login/', views.login_page, name='login'),
    path('register/', views.register_page, name='register'),
    path('accounts/change-password/', views.change_password_page, name='change-password'),
    path('accounts/logout/', views.logout_page, name='logout'),
    path('api/sensors/ingest/', views.sensor_ingest, name='sensor-ingest'),
    path('api/sensors/latest/', views.sensor_latest, name='sensor-latest'),
    path('api/sensors/chart/', views.sensor_chart, name='sensor-chart'),
    path('api/sensors/list/', views.sensor_list, name='sensor-list'),
    path('api/sensors/export/', views.sensor_export_csv, name='sensor-export'),
    path('api/sensors-data/export/', views.sensor_export_csv, name='sensor-data-export'),
    path('api/iot/sensor-data/latest/', views.sensor_latest, name='iot-sensor-latest'),
    path('api/iot/sensor-data/ingest/', views.sensor_ingest, name='iot-sensor-ingest'),
    # Canonical clean routes (used by bridge + dashboard JS)
    path('api/iot/sensor-ingest/', views.sensor_ingest, name='iot-sensor-ingest-clean'),
    path('api/iot/sensor-latest/', views.sensor_latest, name='iot-sensor-latest-clean'),
    path('api/iot/sensor-chart/', views.sensor_chart, name='iot-sensor-chart-clean'),
    path('api/iot/sensor-list/', views.sensor_list, name='iot-sensor-list-clean'),
    path('api/iot/sensor-export/', views.sensor_export_csv, name='iot-sensor-export-clean'),
    path('api/iot/latest-capture/', views.latest_capture_api, name='iot-latest-capture'),
    path('api/iot/camera-proxy/', views.camera_proxy, name='iot-camera-proxy'),
    path('api/iot/sync-now/', views.sync_now, name='iot-sync-now'),
    path('api/upload/', views.ImageUploadView.as_view(), name='image-upload'),
    path('api/latest-scan/', views.latest_scan_api, name='latest-scan'),
    path('api/scans/export/', views.export_scans_csv, name='export-scans'),
    path('api/scans/<int:scan_id>/archive/', views.archive_scan, name='archive-scan'),
    path('api/scans/<int:scan_id>/delete/', views.delete_scan, name='archive-scan'),
    path('api/map-data/', views.map_data_api, name='map-data'),
    path('api/chatbot/', views.chatbot_api, name='chatbot'),
    path('api/reports/generate/', views.generate_report_api, name='generate-report'),
    path('api/esp32-config/', views.esp32_config_api, name='esp32-config'),
    # Alias singulier /api/scan/ vers le detail du DRF router
    path('api/scan/<int:scan_id>/', views.scan_detail_api, name='scan-detail'),
    path('api/debug/routes/', views.debug_routes, name='debug-routes'),
    path('api/', include(router.urls)),
    # RELOAD-FORCE-v6 : modifie pour forcer le reload du runserver
]
