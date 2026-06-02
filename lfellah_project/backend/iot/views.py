import json
from rest_framework import viewsets, permissions, status, generics
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from django.utils import timezone
from django.shortcuts import get_object_or_404, render
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.csrf import csrf_exempt
from core.views_auth import is_iot_staff

from .models import Device, SensorReading, PumpCommand, SensorData
from .serializers import (
    DeviceSerializer, SensorReadingSerializer, SensorReadingCreateSerializer,
    PumpCommandSerializer, PumpControlSerializer,
    SensorDataSerializer, SensorDataCreateSerializer,
)
from .permissions import IsDeviceOwner, IsAdminOrOwner


class DeviceViewSet(viewsets.ModelViewSet):
    serializer_class = DeviceSerializer
    permission_classes = [permissions.IsAuthenticated, IsDeviceOwner]

    def get_queryset(self):
        if self.request.user.role == 'admin':
            return Device.objects.select_related('owner').prefetch_related('config').all()
        return Device.objects.select_related('owner').prefetch_related('config').filter(owner=self.request.user)

    def perform_create(self, serializer):
        import uuid
        serializer.save(owner=self.request.user, device_token=uuid.uuid4().hex[:32])


class SensorReadingViewSet(viewsets.ModelViewSet):
    serializer_class = SensorReadingSerializer
    permission_classes = [permissions.IsAuthenticated, IsDeviceOwner]
    http_method_names = ['get']  # Read-only via API
    lookup_field = 'id'

    def get_queryset(self):
        device_id = self.request.query_params.get('device_id')
        qs = SensorReading.objects.select_related('device').filter(device__owner=self.request.user)
        if device_id:
            qs = qs.filter(device_id=device_id)
        return qs.order_by('-recorded_at')


@api_view(['POST'])
@permission_classes([])
@authentication_classes([])
def sensor_data_ingest(request):
    """
    Endpoint IoT : Reçoit les données des capteurs ESP32/Arduino.
    Authentification par device_token (pas de JWT).
    ---
    POST /api/iot/sensor-data/
    {
        "device_token": "abc123...",
        "readings": [
            {"sensor_type": "ph", "value": 6.5, "unit": "pH"},
            {"sensor_type": "humidity_soil", "value": 45.2, "unit": "%"},
            {"sensor_type": "temperature_air", "value": 28.3, "unit": "C"}
        ]
    }
    """
    device_token = request.data.get('device_token')
    if not device_token:
        return Response({'error': 'device_token requis.'}, status=400)

    device = get_object_or_404(Device, device_token=device_token, is_active=True)
    device.status = 'online'
    device.last_seen = timezone.now()
    device.save(update_fields=['status', 'last_seen'])

    readings = request.data.get('readings', [])
    created = []
    for r in readings:
        unit = r.get('unit', '')
        if r['sensor_type'] == 'ph' and not unit:
            unit = 'pH'
        elif r['sensor_type'] in ('humidity_soil',) and not unit:
            unit = '%'
        elif r['sensor_type'] in ('temperature_air', 'temperature_soil') and not unit:
            unit = 'C'
        elif r['sensor_type'] == 'light' and not unit:
            unit = 'lux'
        elif r['sensor_type'] == 'co2' and not unit:
            unit = 'ppm'

        reading = SensorReading.objects.create(
            device=device,
            sensor_type=r['sensor_type'],
            value=float(r['value']),
            unit=unit,
        )
        created.append(SensorReadingSerializer(reading).data)

    return Response({
        'status': 'success',
        'device': device.name,
        'readings_count': len(created),
        'readings': created,
    }, status=status.HTTP_201_CREATED)


class PumpCommandViewSet(viewsets.ModelViewSet):
    serializer_class = PumpCommandSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrOwner]

    def get_queryset(self):
        return PumpCommand.objects.select_related('device', 'created_by').filter(
            device__owner=self.request.user
        ).order_by('-created_at')

    def perform_create(self, serializer):
        device = get_object_or_404(Device, id=self.request.data.get('device'), owner=self.request.user)
        serializer.save(device=device, created_by=self.request.user)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def device_pump_status(request, device_id):
    """
    GET /api/iot/devices/{device_id}/pump-status/
    Retourne le dernier état de la pompe pour ce device.
    """
    device = get_object_or_404(Device, id=device_id, owner=request.user)
    last_cmd = PumpCommand.objects.filter(device=device).order_by('-created_at').first()
    if last_cmd:
        return Response({
            'device_id': device.id,
            'device_name': device.name,
            'pump_status': last_cmd.command,
            'last_command_at': last_cmd.created_at,
            'command_status': last_cmd.status,
        })
    return Response({
        'device_id': device.id,
        'device_name': device.name,
        'pump_status': 'unknown',
        'last_command_at': None,
        'command_status': None,
    })


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def pump_control(request):
    """
    POST /api/iot/pump-control/
    {"device_id": 1, "command": "on", "duration_seconds": 60}
    """
    serializer = PumpControlSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    device = get_object_or_404(Device, id=serializer.validated_data['device_id'], owner=request.user)

    cmd = PumpCommand.objects.create(
        device=device,
        command=serializer.validated_data['command'],
        duration_seconds=serializer.validated_data.get('duration_seconds') or 0,
        created_by=request.user,
        status='sent',
    )

    # Logique de notification à l'ESP32 via WebSocket / MQTT / Polling
    # L'ESP32 récupère les commandes en polling GET /api/iot/devices/{id}/pending-commands/

    return Response({
        'status': 'success',
        'command_id': cmd.id,
        'message': f"Commande POMPE {cmd.command.upper()} envoyée au device {device.name}",
    })


@api_view(['GET'])
@permission_classes([])
@authentication_classes([])
def device_pending_commands(request, device_token):
    """
    GET /api/iot/pending-commands/?token=<device_token>
    Endpoint pour l'ESP32 : récupère les commandes en attente.
    """
    device = get_object_or_404(Device, device_token=device_token, is_active=True)
    device.status = 'online'
    device.last_seen = timezone.now()
    device.save(update_fields=['status', 'last_seen'])

    # Récupérer les commandes non exécutées
    pending = PumpCommand.objects.filter(device=device, status__in=['pending', 'sent']).order_by('created_at')
    commands_data = []
    for cmd in pending:
        commands_data.append({
            'id': cmd.id,
            'command': cmd.command,
            'duration_seconds': cmd.duration_seconds,
        })
        cmd.status = 'executed'
        cmd.executed_at = timezone.now()
        cmd.save(update_fields=['status', 'executed_at'])

    return Response({
        'device': device.name,
        'pending_commands': commands_data,
        'config': {
            'use_deep_sleep': device.config.use_deep_sleep if hasattr(device, 'config') else False,
            'sleep_duration': device.config.sleep_duration if hasattr(device, 'config') else 300,
            'use_flash': device.config.use_flash if hasattr(device, 'config') else False,
        },
    })


# ─── SENSOR DATA INGEST (ARDUINO NODE) ──────────────────────────

@csrf_exempt
@api_view(['POST'])
@permission_classes([])
@authentication_classes([])
def sensor_data_ingest_v2(request):
    raw_body = request.body

    parsed_body = {}
    try:
        parsed_body = json.loads(raw_body.decode('utf-8', errors='replace')) if raw_body else {}
    except Exception as e:
        print(f'[INGEST][PARSE ERROR] {e} | RAW HEX: {raw_body.hex() if isinstance(raw_body, bytes) else raw_body}')
        return Response({'error': f'JSON parse failed: {e}'}, status=400)

    print(f'[INGEST] >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>')
    print(f'[INGEST] DEBUG DATA: {parsed_body}')
    print(f'[INGEST] Keys recues: {list(parsed_body.keys())}')
    print(f'[INGEST] <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<')

    expected = ['device_token', 'temperature', 'humidity', 'tds', 'ph']
    missing = [k for k in expected if k not in parsed_body]
    if missing:
        print(f'[INGEST] CHAMPS MANQUANTS: {missing}')

    serializer = SensorDataCreateSerializer(data=parsed_body)
    if not serializer.is_valid():
        print(f'[INGEST] VALIDATION FAILED: {serializer.errors}')
        print(f'[INGEST] CHAMPS RECUS vs ATTENDUS:')
        for k, v in parsed_body.items():
            print(f'  - {k}: {v} (type={type(v).__name__})')
        return Response({'error': serializer.errors, 'received': parsed_body}, status=400)

    data = serializer.validated_data
    print(f'[INGEST] VALID: token={data.get("device_token")} T={data.get("temperature")} H={data.get("humidity")} TDS={data.get("tds")} pH={data.get("ph")}')

    try:
        device = Device.objects.get(device_token=data['device_token'], is_active=True)
    except Device.DoesNotExist:
        print(f'[INGEST] DEVICE NOT FOUND: token={data["device_token"]}')
        return Response({'error': 'Device not found or inactive', 'token': data['device_token']}, status=404)

    device.status = 'online'
    device.last_seen = timezone.now()
    device.save(update_fields=['status', 'last_seen'])

    sd = SensorData.objects.create(
        device=device,
        temperature=data.get('temperature'),
        humidity=data.get('humidity'),
        tds=data.get('tds'),
        ph=data.get('ph'),
    )

    return Response({
        'status': 'ok',
        'id': sd.id,
        'device': device.name,
        'recorded_at': sd.recorded_at.isoformat(),
    }, status=201)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def sensor_data_api(request):
    """Retourne les dernieres donnees capteurs pour le dashboard (Chart.js)."""
    device_id = request.query_params.get('device_id')
    limit = int(request.query_params.get('limit', 50))
    qs = SensorData.objects.select_related('device')
    if device_id:
        qs = qs.filter(device_id=device_id)
    elif request.user.role in ('admin', 'agronomist') and not request.user.groups.filter(name='Finance').exists():
        qs = qs.all()
    else:
        qs = qs.filter(device__owner=request.user)
    qs = qs.order_by('-recorded_at')[:limit]

    data = [{
        'id': sd.id,
        'device_name': sd.device.name,
        'temperature': sd.temperature,
        'humidity': sd.humidity,
        'tds': sd.tds,
        'ph': sd.ph,
        'recorded_at': sd.recorded_at.isoformat(),
    } for sd in qs]

    return Response({'results': data, 'count': len(data)})


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def sensor_data_chart_api(request):
    """Retourne les donnees formatees pour Chart.js (labels + datasets)."""
    device_id = request.query_params.get('device_id')
    limit = int(request.query_params.get('limit', 30))
    qs = SensorData.objects.select_related('device')
    if device_id:
        qs = qs.filter(device_id=device_id)
    elif request.user.role in ('admin', 'agronomist') and not request.user.groups.filter(name='Finance').exists():
        qs = qs.all()
    else:
        qs = qs.filter(device__owner=request.user)
    qs = qs.order_by('recorded_at')[:limit]

    labels = []
    temp_data = []
    humid_data = []
    tds_data = []
    ph_data = []

    for sd in qs:
        labels.append(sd.recorded_at.strftime('%H:%M'))
        temp_data.append(sd.temperature)
        humid_data.append(sd.humidity)
        tds_data.append(sd.tds)
        ph_data.append(sd.ph)

    return Response({
        'labels': labels,
        'datasets': {
            'temperature': temp_data,
            'humidity': humid_data,
            'tds': tds_data,
            'ph': ph_data,
        }
    })


# ─── DASHBOARD CAPTEURS HTML ────────────────────────────────────

@login_required
@user_passes_test(is_iot_staff, login_url='/', redirect_field_name=None)
def sensor_dashboard_page(request):
    devices = Device.objects.filter(owner=request.user, is_active=True)
    return render(request, 'dashboard/sensor_dashboard.html', {
        'devices': devices,
    })


# ─── LATEST SENSOR DATA (pour dashboard IoT temps reel) ────────────

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def latest_sensor_data(request):
    """Retourne le dernier relevé capteur au format utilisable par le dashboard IoT."""
    qs = SensorData.objects.select_related('device')
    if request.user.role in ('admin', 'agronomist') and not request.user.groups.filter(name='Finance').exists():
        qs = qs.all()
    else:
        qs = qs.filter(device__owner=request.user)
    sd = qs.order_by('-recorded_at').first()

    if not sd:
        return Response({'has_data': False})

    # Alerts basées sur les seuils
    alerts = []
    if sd.ph and sd.ph < 5.5:
        alerts.append({'type': 'critical', 'msg': f'pH bas : {sd.ph} (seuil: 5.5)'})
    elif sd.ph and sd.ph < 6.0:
        alerts.append({'type': 'warning', 'msg': f'pH faible : {sd.ph}'})
    if sd.tds and sd.tds > 1000:
        alerts.append({'type': 'warning', 'msg': f'TDS eleve : {sd.tds} ppm'})
    if sd.temperature and sd.temperature > 40:
        alerts.append({'type': 'critical', 'msg': f'Temperature elevee : {sd.temperature}°C'})
    if sd.humidity and sd.humidity < 30:
        alerts.append({'type': 'warning', 'msg': f'Humidite basse : {sd.humidity}%'})

    return Response({
        'has_data': True,
        'device_name': sd.device.name,
        'temperature': sd.temperature,
        'humidity': sd.humidity,
        'tds': sd.tds,
        'ph': sd.ph,
        'recorded_at': sd.recorded_at.isoformat(),
        'alerts': alerts,
        'status': 'critical' if any(a['type'] == 'critical' for a in alerts) else (
            'warning' if alerts else 'normal'
        ),
    })
