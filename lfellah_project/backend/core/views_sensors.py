import json
import csv
import os
import time
from datetime import datetime
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.response import Response
from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from .views_auth import IsIotStaff
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from django.shortcuts import render
from django.conf import settings
from django.db.utils import OperationalError
from django.contrib.auth.decorators import user_passes_test
from core.views_auth import is_iot_staff


def _retry_mysql(action, max_retries=3):
    """Exponential retry pour MySQL. Si echec apres N tentatives, retourne l'exception."""
    for attempt in range(max_retries):
        try:
            return action(), False, 'mysql'
        except OperationalError as e:
            wait = 2 ** attempt
            if attempt < max_retries - 1:
                print(f'[RETRY] MySQL tentative {attempt+1}/{max_retries} echouee, '
                      f'nouvelle tentative dans {wait}s...')
                time.sleep(wait)
            else:
                return None, True, e
    return None, True, OperationalError('max retries exceeded')


@user_passes_test(is_iot_staff, login_url='/', redirect_field_name=None)
def sensor_dashboard(request):
    """Dashboard IoT — utilise le nouveau template sensor_dashboard.html."""
    from core.models import PlantScan
    recent_scans = PlantScan.objects.select_related('device').order_by('-scanned_at')[:20]
    latest_scan = recent_scans.first()
    return render(request, 'dashboard/sensor_dashboard.html', {
        'history': recent_scans,
        'scan': latest_scan,
    })


def map_sensor_payload(data):
    if not data:
        return None
    mapped = {}
    temp_keys = ['temperature', 'temp', 'Temperature', 'T', 'air_temp']
    hum_keys  = ['humidity', 'hum', 'Humidity', 'H', 'air_humidity']
    tds_keys  = ['tds', 'TDS', 'Tds']
    ph_keys   = ['ph', 'pH', 'PH', 'Ph']
    soil_keys = ['soil_moisture', 'soil', 'soil_moisture', 'Soil']

    def _extract(keys):
        for k in keys:
            if k in data and data[k] not in (None, '', 'null'):
                try:
                    return float(data[k])
                except (ValueError, TypeError):
                    continue
        return 0.0  # fallback: capteur absent

    mapped['temperature']   = _extract(temp_keys)
    mapped['humidity']      = _extract(hum_keys)
    mapped['tds']           = _extract(tds_keys)
    mapped['ph']            = _extract(ph_keys)
    mapped['soil_moisture'] = _extract(soil_keys)
    mapped['relay']         = data.get('relay')
    mapped['mode']          = data.get('mode')
    mapped['device_token'] = data.get('device_token', '')
    return mapped if mapped.get('device_token') else None


def validate_payload(payload):
    if not payload:
        return False, ['payload is None or empty']
    required = ['device_token']
    optional = ['temperature', 'humidity', 'tds', 'ph']
    missing = [f for f in required if not payload.get(f)]
    has_sensor_data = any(payload.get(f) is not None for f in optional)
    if not has_sensor_data:
        missing.append('at least one sensor value')
    return len(missing) == 0, missing


class SensorDataIngestSerializer(serializers.Serializer):
    device_token = serializers.CharField(required=True, min_length=1)
    temperature = serializers.FloatField(required=False, allow_null=True)
    humidity = serializers.FloatField(required=False, allow_null=True)
    tds = serializers.FloatField(required=False, allow_null=True)
    ph = serializers.FloatField(required=False, allow_null=True)
    soil_moisture = serializers.FloatField(required=False, allow_null=True)
    relay = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    mode = serializers.CharField(required=False, allow_null=True, allow_blank=True)

    def validate(self, attrs):
        has_sensor_data = any(
            attrs.get(f) is not None
            for f in ('temperature', 'humidity', 'tds', 'ph')
        )
        if not has_sensor_data:
            raise serializers.ValidationError(
                'Au moins une valeur capteur (temperature, humidity, tds, ph) est requise.'
            )
        return attrs


@csrf_exempt
@api_view(['POST'])
@permission_classes([])
@authentication_classes([])
def sensor_ingest(request):
    raw_body = request.body
    try:
        decoded = raw_body.decode('utf-8', errors='replace') if isinstance(raw_body, bytes) else str(raw_body)
        parsed_body = json.loads(decoded) if decoded.strip() else {}
        print(f"DEBUG: Données reçues : {parsed_body}, Time: {timezone.now()}")
        print(f'[DEBUG INGEST] KEYS: {list(parsed_body.keys())}')
    except Exception as e:
        return Response({'error': f'JSON parse failed: {e}'}, status=400)

    mapped = map_sensor_payload(parsed_body)
    if not mapped:
        return Response({'error': 'Mapping failed: device_token manquant'}, status=400)

    is_valid, missing = validate_payload(mapped)
    if not is_valid:
        return Response({'error': f'Champs manquants: {missing}'}, status=400)

    # Validation via le serializer DRF (assure que temp/hum/tds/ph sont acceptes)
    serializer = SensorDataIngestSerializer(data=mapped)
    if not serializer.is_valid():
        print(f'[INGEST] Validation DRF echouee : {serializer.errors}')
        return Response({'error': 'Validation failed', 'details': serializer.errors}, status=400)

    from iot.models import Device, SensorData
    from django.db import transaction

    token = mapped['device_token']
    device = None
    device_db = 'mysql'

    # Essayer MySQL d'abord, puis SQLite
    try:
        device = Device.objects.get(device_token=token, is_active=True)
        device_db = 'mysql'
    except Device.DoesNotExist:
        pass
    except OperationalError:
        pass

    if device is None:
        try:
            device = Device.objects.using('default').get(device_token=token, is_active=True)
            device_db = 'default'
            print(f'[INGEST] Device trouve dans SQLite (fallback) : {device.name}')
        except Device.DoesNotExist:
            return Response({'error': f'Device not found: {token}'}, status=404)

    if device is None:
        return Response({'error': f'Device not found: {token}'}, status=404)

    # ─── DEBUG TRANSPARENCE ─────────────────────────────────────────
    print(f'[DEBUG] DB utilisee : {device_db}')
    print(f'[DEBUG] Timestamp recu (payload) : {mapped.get("recorded_at", "non fourni")}')
    print(f'[DEBUG] Timestamp serveur : {timezone.now().isoformat()}')
    print(f'[DEBUG] ID Device : {device.id} (name={device.name})')
    # ────────────────────────────────────────────────────────────────

    device.status = 'online'
    device.last_seen = timezone.now()
    try:
        device.save(using=device_db, update_fields=['status', 'last_seen'])
        print(f'[DEBUG] Device save status : succes ({device_db})')
    except Exception as e:
        print(f'[DEBUG] Device save status : echec ({device_db}) — {type(e).__name__}: {e}')

    sd = None
    used_db = device_db

    if device_db == 'default':
        # Device is in SQLite, write SensorData there too to avoid FK cross-DB error
        print('[INGEST] Device in SQLite — ecriture SensorData dans SQLite')
        sd = SensorData.objects.using('default').create(
            device=device,
            temperature=mapped.get('temperature'),
            humidity=mapped.get('humidity'),
            tds=mapped.get('tds'),
            ph=mapped.get('ph'),
            soil_moisture=mapped.get('soil_moisture'),
            relay=mapped.get('relay'),
            mode=mapped.get('mode'),
            recorded_at=timezone.now(),
        )
        # Forcer le commit explicite (meme si auto-commit par defaut)
        transaction.commit(using='default')
    else:
        # Device in MySQL, try MySQL write with exponential retry
        def _create():
            return SensorData.objects.create(
                device=device,
                temperature=mapped.get('temperature'),
                humidity=mapped.get('humidity'),
                tds=mapped.get('tds'),
                ph=mapped.get('ph'),
                soil_moisture=mapped.get('soil_moisture'),
                relay=mapped.get('relay'),
                mode=mapped.get('mode'),
                recorded_at=timezone.now(),
            )

        sd, fallback, err = _retry_mysql(_create)
        if fallback:
            print(f'[INGEST] ERREUR CRITIQUE: MySQL indisponible apres 3 tentatives — donnees NON sauvegardees')
            print(f'[INGEST] Derniere erreur MySQL: {err}')
            return Response({
                'error': 'MySQL indisponible',
                'detail': str(err),
            }, status=503)
        # Forcer le commit explicite sur MySQL
        transaction.commit(using='mysql')

    # ─── VERIFICATION IMMEDIATE PERSISTANCE ─────────────────────────
    try:
        exists = SensorData.objects.using(used_db).filter(id=sd.id).exists()
        print(f'[DEBUG] Save status : succes | record id={sd.id} existe dans {used_db} = {exists}')
    except Exception as e:
        print(f'[DEBUG] Save status : echec verification — {type(e).__name__}: {e}')
        exists = False

    if used_db == 'mysql' and not exists:
        print(f'[CRITICAL] MySQL commit semble reussi mais record id={sd.id} introuvable immediatement!')
    # ────────────────────────────────────────────────────────────────

    print(f'[INGEST] Persiste [{used_db}] id={sd.id} | '
          f'T={sd.temperature} H={sd.humidity} TDS={sd.tds} pH={sd.ph}')
    print(f'DEBUG: Data saved to DB: {parsed_body}')
    print(f'DEBUG: Received Arduino values: {parsed_body}, Saving to DB with mapping: '
          f'{{temp: {sd.temperature}, hum: {sd.humidity}, tds: {sd.tds}, ph: {sd.ph}}}')

    # Smart Advisor — alerte email asynchrone (non-bloquant)
    from core.utils import async_check_and_notify
    async_check_and_notify({
        'temperature': sd.temperature,
        'humidity': sd.humidity,
        'tds': sd.tds,
        'ph': sd.ph,
        'soil_moisture': sd.soil_moisture,
    })

    return Response({
        'status': 'ok',
        'id': sd.id,
        'device': device.name,
        'recorded_at': sd.recorded_at.isoformat(),
        'db': used_db,
        'verified': exists,
    }, status=201)


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsIotStaff])
def sensor_latest(request):
    from iot.models import Device, SensorData

    offline_mode = False
    sd = None

    try:
        qs = SensorData.objects.select_related('device').order_by('-recorded_at')
        sd = qs.first()
    except OperationalError as e:
        offline_mode = True
        print(f'[LATEST] ERREUR: MySQL indisponible — {e}')
        resp = Response({
            'has_data': False,
            'offline_mode': True,
            'error': 'MySQL indisponible',
            'detail': str(e),
        })
        resp['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        resp['Pragma'] = 'no-cache'
        resp['Expires'] = '0'
        return resp

    if not sd:
        resp = Response({'has_data': False, 'offline_mode': False})
        resp['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        resp['Pragma'] = 'no-cache'
        resp['Expires'] = '0'
        return resp

    # Audit latence DB -> API
    age_sec = (timezone.now() - sd.recorded_at).total_seconds()
    print(f"[LATEST] Audit recorded_at={sd.recorded_at.isoformat()} | age={age_sec:.1f}s")

    alerts = []
    if sd.ph and sd.ph < 5.5:
        alerts.append({'type': 'critical', 'msg': f'pH bas: {sd.ph} (seuil: 5.5)'})
    elif sd.ph and sd.ph < 6.0:
        alerts.append({'type': 'warning', 'msg': f'pH faible: {sd.ph}'})
    if sd.tds and sd.tds > 1000:
        alerts.append({'type': 'warning', 'msg': f'TDS eleve: {sd.tds} ppm'})
    if sd.temperature and sd.temperature > 40:
        alerts.append({'type': 'critical', 'msg': f'Temperature elevee: {sd.temperature}C'})
    if sd.humidity and sd.humidity < 30:
        alerts.append({'type': 'warning', 'msg': f'Humidite basse: {sd.humidity}%'})

    # Warning si données périmées (>60s) — laisse la marge au bridge serial
    stale_warning = age_sec > 60
    if stale_warning:
        alerts.append({'type': 'warning', 'msg': f'Donnees perimees (dernier enregistrement il y a {int(age_sec)}s)'})

    response_data = {
        'has_data': True,
        'device_name': sd.device.name,
        'temperature': sd.temperature,
        'humidity': sd.humidity,
        'tds': sd.tds,
        'ph': sd.ph,
        'soil_moisture': sd.soil_moisture,
        'relay': sd.relay,
        'mode': sd.mode,
        'recorded_at': sd.recorded_at.isoformat(),
        'recorded_at_ms': int(sd.recorded_at.timestamp() * 1000),
        'offline_mode': offline_mode,
        'alerts': alerts,
        'stale_warning': stale_warning,
        'stale_msg': 'Donnees perimees' if stale_warning else None,
        'status': 'critical' if any(a['type'] == 'critical' for a in alerts) else (
            'warning' if alerts else 'normal'
        ),
    }
    print(f"[LATEST] Envoi donnees : {sd.recorded_at.isoformat()} | age={age_sec:.1f}s | T={sd.temperature} H={sd.humidity} TDS={sd.tds} pH={sd.ph}")
    resp = Response(response_data)
    resp['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    resp['Pragma'] = 'no-cache'
    resp['Expires'] = '0'
    return resp


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsIotStaff])
def sensor_chart(request):
    from iot.models import SensorData
    device_id = request.query_params.get('device_id')
    limit = int(request.query_params.get('limit', 30))

    qs = SensorData.objects.select_related('device').order_by('recorded_at')
    if device_id:
        qs = qs.filter(device_id=device_id)
    qs = qs[:limit]

    labels = []
    temp_data, humid_data, tds_data, ph_data = [], [], [], []

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


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsIotStaff])
def sensor_list(request):
    from iot.models import SensorData
    device_id = request.query_params.get('device_id')
    limit = int(request.query_params.get('limit', 50))

    qs = SensorData.objects.select_related('device').order_by('-recorded_at')
    if device_id:
        qs = qs.filter(device_id=device_id)
    qs = qs[:limit]

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
@permission_classes([IsAuthenticated, IsIotStaff])
def sensor_export_csv(request):
    from iot.models import SensorData
    device_id = request.query_params.get('device_id')
    date_from = request.query_params.get('from')
    date_to = request.query_params.get('to')

    qs = SensorData.objects.select_related('device').order_by('-recorded_at')
    if device_id:
        qs = qs.filter(device_id=device_id)
    if date_from:
        qs = qs.filter(recorded_at__gte=date_from)
    if date_to:
        qs = qs.filter(recorded_at__lte=date_to)

    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="sensor_data_' + datetime.now().strftime('%Y%m%d_%H%M%S') + '.csv"'
    writer = csv.writer(response)
    writer.writerow(['Date', 'Appareil', 'Temperature (C)', 'Humidite (%)', 'TDS (ppm)', 'pH'])
    for sd in qs:
        writer.writerow([
            sd.recorded_at.strftime('%Y-%m-%d %H:%M:%S'),
            sd.device.name if sd.device else '',
            sd.temperature or '',
            sd.humidity or '',
            sd.tds or '',
            sd.ph or '',
        ])
    return response


@api_view(['POST'])
@permission_classes([])
@authentication_classes([])
def sync_now(request):
    """
    Declenche une synchronisation immediate SQLite (default) → MySQL (mysql).
    Appele par le bridge quand il detecte que MySQL est revenu en ligne.
    Transfert toutes les donnees SensorData du buffer SQLite vers MySQL,
    puis vide le buffer SQLite.
    """
    from iot.models import SensorData, Device
    from core.db_router import PrimaryReplicaRouter

    # Verifier que MySQL est disponible
    if not PrimaryReplicaRouter.is_mysql_available():
        print('[SYNC-NOW] MySQL indisponible — synchronisation annulee')
        return Response({
            'status': 'skipped',
            'reason': 'MySQL indisponible',
            'synced': 0,
        })

    # Lire les enregistrements du buffer SQLite
    records = list(
        SensorData.objects.using('default')
        .select_related('device')
        .order_by('recorded_at')
    )

    if not records:
        print('[SYNC-NOW] Aucune donnee a synchroniser dans SQLite')
        return Response({
            'status': 'ok',
            'reason': 'Buffer SQLite vide',
            'synced': 0,
        })

    # Inserer dans MySQL
    new_objects = []
    for sd in records:
        new_objects.append(SensorData(
            device=sd.device,
            temperature=sd.temperature,
            humidity=sd.humidity,
            tds=sd.tds,
            ph=sd.ph,
            recorded_at=sd.recorded_at,
        ))

    try:
        SensorData.objects.using('mysql').bulk_create(new_objects)
        synced = len(new_objects)
        print(f'[SYNC-NOW] {synced} enregistrements transferes SQLite → MySQL')

        # Supprimer du buffer SQLite
        sqlite_ids = [sd.id for sd in records]
        deleted, _ = SensorData.objects.using('default').filter(id__in=sqlite_ids).delete()
        print(f'[SYNC-NOW] {deleted} enregistrements supprimes du buffer SQLite')

        return Response({
            'status': 'ok',
            'synced': synced,
            'deleted_from_buffer': deleted,
        })
    except OperationalError:
        return Response({
            'status': 'error',
            'reason': 'Echec ecriture MySQL — buffer SQLite preserve',
            'synced': 0,
        })
    except Exception as e:
        return Response({
            'status': 'error',
            'reason': str(e),
            'synced': 0,
        })


@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated, IsIotStaff])
def irrigation_control(request):
    """
    Controle pompe d'irrigation via relais Arduino.
    POST /api/iot/irrigation-control/
    Body: {"action": "on"} ou {"action": "off"} ou {"action": "auto"} ou {"action": "status"}
          {"action": "mode_auto"} ou {"action": "mode_manual"} pour basculer le mode.
    Ecrit dans irrigation_command.txt que le bridge lit periodiquement.
    """
    action = request.data.get('action', '').lower()

    valid_actions = ('on', 'off', 'status', 'auto', 'mode_auto', 'mode_manual')
    if action not in valid_actions:
        return Response({'error': f'Action invalide. Utiliser {", ".join(valid_actions)}'}, status=400)

    cmd_map = {
        'on': 'RELAY:ON',
        'off': 'RELAY:OFF',
        'auto': 'AUTO',
        'status': 'STATUS',
        'mode_auto': 'A',
        'mode_manual': 'M',
    }
    serial_cmd = cmd_map[action]
    command_file = os.path.join(settings.BASE_DIR, 'irrigation_command.txt')

    with open(command_file, 'w') as f:
        f.write(serial_cmd)

    mode_response = {
        'mode_auto': 'AUTO',
        'mode_manual': 'MANUAL',
    }.get(action)

    return Response({
        'status': 'ok',
        'action': action,
        'command': serial_cmd,
        'mode': mode_response,
        'message': f'Commande {serial_cmd} envoyee au bridge',
    })
