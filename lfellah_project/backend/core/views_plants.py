from rest_framework import viewsets, permissions, status, generics, serializers
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes, authentication_classes, action
from rest_framework.permissions import IsAuthenticated
from core.views_auth import IsIotStaff
from django.shortcuts import render, redirect
from django.http import HttpResponse, FileResponse
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta
import csv
import os
import requests

from .models import PlantScan, Alert
from .serializers import PlantScanSerializer, PlantScanListSerializer, AlertSerializer
from .predictor import predict_plant_disease


class PlantScanViewSet(viewsets.ModelViewSet):
    queryset = PlantScan.objects.select_related('user', 'device').order_by('-scanned_at')
    permission_classes = []  # Dashboard public
    authentication_classes = []

    def get_serializer_class(self):
        if self.action == 'list':
            return PlantScanListSerializer
        return PlantScanSerializer

    def get_queryset(self):
        qs = self.queryset
        user = getattr(self.request, 'user', None)
        if user and user.is_authenticated and user.role not in ('admin', 'agronomist'):
            qs = qs.filter(Q(user=user) | Q(user__isnull=True))
        severity = self.request.query_params.get('severity')
        if severity:
            qs = qs.filter(severity=severity)
        is_archived = self.request.query_params.get('archived')
        if is_archived is not None:
            qs = qs.filter(is_archived=is_archived == 'true')
        return qs


class ImageUploadView(generics.CreateAPIView):
    """Upload d'image + prediction IA (ESP32 ou manuel)"""
    parser_classes = [MultiPartParser, FormParser]
    serializer_class = PlantScanSerializer
    permission_classes = []  # ESP32 sans auth
    authentication_classes = []

    def create(self, request, *args, **kwargs):
        image = request.FILES.get('image')
        if not image:
            return Response({'error': 'Aucune image fournie.'}, status=status.HTTP_400_BAD_REQUEST)

        lat = request.data.get('latitude')
        lon = request.data.get('longitude')
        lang = request.data.get('lang', 'fr')
        device_token = request.data.get('device_token')

        from iot.models import Device
        device = None
        if device_token:
            device = Device.objects.filter(device_token=device_token).first()
            if device:
                device.status = 'online'
                device.last_seen = timezone.now()
                device.save(update_fields=['status', 'last_seen'])

        scan = PlantScan.objects.create(
            user=request.user if request.user.is_authenticated else None,
            image=image,
            latitude=float(lat) if lat else None,
            longitude=float(lon) if lon else None,
            device=device,
        )

        image_path = scan.image.path
        result = predict_plant_disease(image_path, lang=lang)
        scan.disease_name = result.get('disease_name', '')
        scan.confidence = result.get('confidence', 0.0)
        scan.severity = result.get('severity', 'warning')
        scan.watering_advice = result.get('watering_advice', '')
        scan.save()

        if scan.severity == 'critical':
            Alert.objects.create(
                scan=scan,
                alert_type='critical_disease',
                message=f"Maladie critique detectee: {scan.disease_name} (confiance: {scan.confidence}%)"
            )

        return Response({
            'status': 'success',
            'id': scan.id,
            'disease_name': scan.disease_name,
            'confidence': scan.confidence,
            'watering_advice': scan.watering_advice,
            'severity': scan.severity,
            'image_url': request.build_absolute_uri(scan.image.url),
        }, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def latest_scan_api(request):
    scan = PlantScan.objects.select_related('device').order_by('-scanned_at').first()
    if scan:
        return Response({
            'status': 'success',
            **PlantScanSerializer(scan, context={'request': request}).data,
        })
    return Response({'status': 'empty'})


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsIotStaff])
def latest_capture_api(request):
    """ESP32-CAM: derniere photo capturee + analyse IA (public, polling JS)."""
    scan = PlantScan.objects.select_related('device').order_by('-scanned_at').first()
    if not scan or not scan.image:
        return Response({
            'has_capture': False,
            'disease_name': 'Aucune capture',
            'confidence': 0,
            'severity': 'normal',
            'watering_advice': 'En attente de la premiere photo ESP32-CAM.',
            'image_url': '',
            'scanned_at': None,
        })
    return Response({
        'has_capture': True,
        'id': scan.id,
        'disease_name': scan.disease_name or 'Analyse en cours...',
        'confidence': scan.confidence or 0,
        'severity': scan.severity or 'normal',
        'watering_advice': scan.watering_advice or '',
        'image_url': request.build_absolute_uri(scan.image.url) if scan.image else '',
        'scanned_at': scan.scanned_at.isoformat() if scan.scanned_at else None,
    })


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def map_data_api(request):
    scans = PlantScan.objects.filter(
        latitude__isnull=False,
        longitude__isnull=False,
    ).values('id', 'disease_name', 'severity', 'latitude', 'longitude',
             'temperature_c', 'humidity_pct', 'scanned_at')
    stats = PlantScan.objects.aggregate(
        total=Count('id'),
        healthy=Count('id', filter=Q(severity='healthy')),
        warning=Count('id', filter=Q(severity='warning')),
        critical=Count('id', filter=Q(severity='critical')),
    )
    return Response({'scans': list(scans), 'stats': stats})


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def archive_scan(request, scan_id):
    scan = PlantScan.objects.get(id=scan_id)
    scan.is_archived = not scan.is_archived
    scan.save(update_fields=['is_archived'])
    return Response({'status': 'success', 'is_archived': scan.is_archived})


@api_view(['DELETE'])
@permission_classes([permissions.IsAuthenticated])
def delete_scan(request, scan_id):
    if request.user.role not in ('admin', 'agronomist'):
        return Response({'error': 'Permission refusee.'}, status=403)
    scan = PlantScan.objects.get(id=scan_id)
    scan.image.delete(save=False)
    scan.delete()
    return Response({'status': 'deleted'})


class AlertViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AlertSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = Alert.objects.select_related('scan').order_by('-created_at')
        unread = self.request.query_params.get('unread_only')
        if unread == 'true':
            qs = qs.filter(is_read=False)
        return qs[:50]

    @action(methods=['POST'], detail=True, url_path='read')
    def mark_read(self, request, pk=None):
        alert = self.get_object()
        alert.is_read = True
        alert.save(update_fields=['is_read'])
        return Response({'status': 'ok'})

    @action(methods=['POST'], detail=False, url_path='read-all')
    def mark_all_read(self, request):
        Alert.objects.filter(is_read=False).update(is_read=True)
        return Response({'status': 'ok'})


@api_view(['GET'])
@permission_classes([])
@authentication_classes([])
def export_scans_csv(request):
    user = getattr(request, 'user', None)
    if user and user.is_authenticated and user.role in ('admin', 'agronomist'):
        qs = PlantScan.objects.order_by('-scanned_at')
    elif user and user.is_authenticated:
        qs = PlantScan.objects.filter(Q(user=user) | Q(user__isnull=True)).order_by('-scanned_at')
    else:
        qs = PlantScan.objects.filter(user__isnull=True).order_by('-scanned_at')
    response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
    response['Content-Disposition'] = 'attachment; filename=scans_export.csv'
    writer = csv.writer(response)
    writer.writerow(['ID', 'Maladie', 'Confiance', 'Gravite', 'Conseil', 'Date'])
    for s in qs:
        writer.writerow([s.id, s.disease_name, s.confidence, s.severity, s.watering_advice, s.scanned_at])
    return response


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsIotStaff])
def camera_proxy(request):
    """
    Proxy ESP32-CAM : evite le CORS cote navigateur en faisant la requete
    image depuis le backend Django vers l'IP locale de la camera.
    """
    camera_url = request.GET.get('url', 'http://192.168.1.27/capture')
    timeout = int(request.GET.get('timeout', 5))
    try:
        r = requests.get(camera_url, timeout=timeout)
        if r.status_code == 200:
            content_type = r.headers.get('Content-Type', 'image/jpeg')
            return HttpResponse(r.content, content_type=content_type)
        return Response({'error': f'Camera returned HTTP {r.status_code}'}, status=502)
    except requests.exceptions.ConnectionError:
        return Response({'error': f'Impossible de se connecter a la camera ({camera_url}). Verifiez qu\'elle est en ligne.'}, status=502)
    except requests.exceptions.Timeout:
        return Response({'error': 'Timeout lors de la connexion a la camera.'}, status=504)
    except Exception as e:
        return Response({'error': f'Erreur proxy camera: {type(e).__name__}: {str(e)}'}, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsIotStaff])
def scan_detail_api(request, scan_id):
    """Alias /api/scan/<id>/ vers le detail d'un scan."""
    from core.models import PlantScan
    try:
        scan = PlantScan.objects.select_related('device').get(id=scan_id)
    except PlantScan.DoesNotExist:
        return Response({'error': 'Scan introuvable'}, status=404)
    return Response({
        'id': scan.id,
        'disease_name': scan.disease_name or 'Inconnu',
        'confidence': scan.confidence,
        'severity': scan.severity or 'normal',
        'watering_advice': scan.watering_advice or '',
        'image_url': request.build_absolute_uri(scan.image.url) if scan.image else '',
        'scanned_at': scan.scanned_at.isoformat() if scan.scanned_at else None,
    })


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated, IsIotStaff])
def esp32_config_api(request):
    """Configuration ESP32-CAM : URL de la camera, intervalle de capture, etc."""
    from django.conf import settings
    camera_url = getattr(settings, 'ESP32_CAMERA_URL', 'http://192.168.1.27/capture')
    capture_interval = getattr(settings, 'ESP32_CAPTURE_INTERVAL', 30)

    if request.method == 'POST':
        # Reception de la config depuis le frontend (langue, etc.)
        # Pas de persistence en DB ici, on retourne juste OK
        return Response({
            'status': 'ok',
            'received': request.data,
            'camera_url': camera_url,
            'capture_interval_sec': capture_interval,
            'server_time': timezone.now().isoformat(),
        })

    return Response({
        'camera_url': camera_url,
        'capture_interval_sec': capture_interval,
        'server_time': timezone.now().isoformat(),
    })
