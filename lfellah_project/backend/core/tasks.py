try:
    from celery import shared_task as _celery_task
    CELERY_AVAILABLE = True
except ImportError:
    CELERY_AVAILABLE = False
    _celery_task = None

from django.utils import timezone
from datetime import timedelta
from django.db.models import Count, Q
import os

def _shared_task(**kw):
    def decorator(func):
        return func
    return decorator


def generate_report_pdf_task(user_id, week_start_str, week_end_str):
    from django.contrib.auth import get_user_model
    from core.models import PlantScan, Report
    from core.report_generator import generate_weekly_report_pdf

    User = get_user_model()
    try:
        user = User.objects.get(id=user_id)
        week_start = timezone.datetime.fromisoformat(week_start_str).date()
        week_end = timezone.datetime.fromisoformat(week_end_str).date()
        scans = PlantScan.objects.filter(scanned_at__date__gte=week_start, scanned_at__date__lte=week_end)
        total = scans.count()
        stats = scans.aggregate(
            critical_count=Count('id', filter=Q(severity='critical')),
            warning_count=Count('id', filter=Q(severity='warning')),
            healthy_count=Count('id', filter=Q(severity='healthy')),
        )
        pdf_path = generate_weekly_report_pdf(
            week_start=week_start, week_end=week_end,
            total_scans=total,
            critical_count=stats['critical_count'],
            warning_count=stats['warning_count'],
            healthy_count=stats['healthy_count'],
            scans=scans[:20],
        )
        Report.objects.create(
            generated_by=user,
            week_start=week_start, week_end=week_end,
            total_scans=total,
            critical_count=stats['critical_count'],
            warning_count=stats['warning_count'],
            healthy_count=stats['healthy_count'],
            pdf_file=pdf_path,
        )
        return f"Report PDF genere pour {week_start} - {week_end}"
    except Exception:
        pass


def check_device_offline_alerts():
    try:
        from iot.models import Device
    except ImportError:
        return "Device model not available"
    from core.models import Alert

    threshold = timezone.now() - timedelta(minutes=30)
    offline_devices = Device.objects.filter(
        is_active=True, last_seen__lt=threshold,
    ).exclude(status='maintenance')

    for device in offline_devices:
        device.status = 'offline'
        device.save(update_fields=['status'])
        recent_alert = Alert.objects.filter(
            alert_type='device_offline',
            message__contains=device.name,
            created_at__gte=timezone.now() - timedelta(hours=1),
        ).exists()
        if not recent_alert:
            Alert.objects.create(
                alert_type='device_offline',
                message=f"Appareil hors ligne : {device.name} ({device.device_type}). Derniere activite : {device.last_seen}",
            )
    return f"{offline_devices.count()} appareils marques hors ligne"