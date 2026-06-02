from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
import csv
from django.http import HttpResponse
from .models import (
    PlantScan, SystemNotification,
    Alert, SecurityLog, BlockedIP, Report, ChatMessage
)

@admin.register(PlantScan)
class PlantScanAdmin(admin.ModelAdmin):
    list_display = ('image_thumbnail', 'disease_name_colored', 'confidence_bar', 'severity_badge', 'scanned_at_formatted')
    list_filter = ('severity', 'scanned_at', 'confidence')
    search_fields = ('disease_name', 'watering_advice', 'severity')
    ordering = ('-scanned_at',)
    readonly_fields = ('scanned_at', 'image_preview')
    actions = ['export_as_csv', 'mark_as_critical', 'mark_as_warning', 'mark_as_normal']
    
    fieldsets = (
        ("Diagnostic IA", {
            'fields': ('disease_name', 'confidence')
        }),
        ("Analyse de Gravité & Recommandations", {
            'fields': ('severity', 'watering_advice')
        }),
        ("Fichier Photo", {
            'fields': ('image', 'image_preview', 'scanned_at')
        }),
    )

    # 1. Thumbnail for the admin list view
    def image_thumbnail(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="width: 50px; height: 50px; object-fit: cover; border-radius: 8px; border: 1px solid #ddd;" />',
                obj.image.url
            )
        return "Aucune image"
    image_thumbnail.short_description = "Aperçu"

    # 2. Large image preview for the detail view
    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="max-width: 300px; max-height: 300px; object-fit: contain; border-radius: 12px; border: 2px solid #ccc;" />',
                obj.image.url
            )
        return "Aucune image"
    image_preview.short_description = "Aperçu de la feuille"

    # 3. Dynamic color for disease name
    def disease_name_colored(self, obj):
        color = "#10b981"  # green
        if obj.severity == 'critical':
            color = "#ef4444"  # red
        elif obj.severity == 'warning':
            color = "#f59e0b"  # orange
        return format_html('<span style="font-weight: bold; color: {};">{}</span>', color, obj.disease_name)
    disease_name_colored.short_description = "Maladie / État"

    # 4. Progress bar style for confidence
    def confidence_bar(self, obj):
        color = "bg-success"
        percent = obj.confidence
        if percent < 50:
            color = "bg-danger"
        elif percent < 80:
            color = "bg-warning"
        
        return format_html(
            '<div class="progress" style="height: 18px; width: 120px; border-radius: 9px; overflow: hidden; background: #e9ecef; margin: 0;">'
            '  <div class="progress-bar {}" role="progressbar" style="width: {}%; font-size: 10px; line-height: 18px; font-weight: bold; color: white;" aria-valuenow="{}" aria-valuemin="0" aria-valuemax="100">{}%</div>'
            '</div>',
            color, percent, percent, round(percent, 1)
        )
    confidence_bar.short_description = "Fiabilité IA"

    # 5. Badges for severity
    def severity_badge(self, obj):
        badge_class = "badge badge-success"
        label = "Saine"
        if obj.severity == 'critical':
            badge_class = "badge badge-danger"
            label = "Critique"
        elif obj.severity == 'warning':
            badge_class = "badge badge-warning text-dark"
            label = "Attention"
        
        return format_html('<span class="{}" style="padding: 4px 8px; font-size: 10px; font-weight: bold; border-radius: 4px;">{}</span>', badge_class, label)
    severity_badge.short_description = "Gravité"

    # 6. Scanned at formatted beautifully
    def scanned_at_formatted(self, obj):
        return obj.scanned_at.strftime("%d/%m/%Y %H:%M")
    scanned_at_formatted.short_description = "Date du Scan"

    # --- Actions ---
    
    # Action to export data as CSV
    def export_as_csv(self, request, queryset):
        meta = self.model._meta
        field_names = [field.name for field in meta.fields]

        response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
        response['Content-Disposition'] = 'attachment; filename=scans_export.csv'
        writer = csv.writer(response)

        # Write header
        writer.writerow(field_names)
        # Write rows
        for obj in queryset:
            row = []
            for field in field_names:
                val = getattr(obj, field)
                if isinstance(val, str):
                    val = val.encode('utf-8').decode('utf-8')
                row.append(val)
            writer.writerow(row)

        return response
    export_as_csv.short_description = "Exporter la sélection en CSV"

    # Bulk severity change actions
    def mark_as_critical(self, request, queryset):
        queryset.update(severity='critical')
        self.message_user(request, "Les scans sélectionnés ont été marqués comme critiques.")
    mark_as_critical.short_description = "Marquer comme Critique"

    def mark_as_warning(self, request, queryset):
        queryset.update(severity='warning')
        self.message_user(request, "Les scans sélectionnés ont été marqués comme warning.")
    mark_as_warning.short_description = "Marquer comme Attention"

    def mark_as_normal(self, request, queryset):
        queryset.update(severity='healthy')
        self.message_user(request, "Les scans s\u00e9lectionn\u00e9s ont \u00e9t\u00e9 marqu\u00e9s comme sains.")
    mark_as_normal.short_description = "Marquer comme Sain"

@admin.register(SystemNotification)
class SystemNotificationAdmin(admin.ModelAdmin):
    list_display = ('type_badge', 'message_excerpt', 'is_read_badge', 'created_at_formatted')
    list_filter = ('type', 'is_read', 'created_at')
    search_fields = ('message',)
    ordering = ('is_read', '-created_at')
    actions = ['mark_as_read', 'mark_as_unread']

    def type_badge(self, obj):
        badge_class = "badge badge-info"
        if obj.type == 'error':
            badge_class = "badge badge-danger"
        elif obj.type == 'warning':
            badge_class = "badge badge-warning text-dark"
        
        return format_html('<span class="{}" style="padding: 4px 8px; font-size: 10px; font-weight: bold; border-radius: 4px;">{}</span>', badge_class, obj.get_type_display())
    type_badge.short_description = "Type"

    def message_excerpt(self, obj):
        color = "#333"
        font_weight = "normal"
        if not obj.is_read:
            font_weight = "bold"
            if obj.type == 'error':
                color = "#ef4444"
        return format_html('<span style="color: {}; font-weight: {};">{}</span>', color, font_weight, obj.message)
    message_excerpt.short_description = "Message de Notification"

    def is_read_badge(self, obj):
        if obj.is_read:
            return format_html('<span class="badge badge-secondary" style="padding: 4px 8px;">Lu</span>')
        return format_html('<span class="badge badge-primary" style="padding: 4px 8px; font-weight: bold;">Non Lu</span>')
    is_read_badge.short_description = "Statut"

    def created_at_formatted(self, obj):
        return obj.created_at.strftime("%d/%m/%Y %H:%M")
    created_at_formatted.short_description = "Date d'alerte"

    # Actions
    def mark_as_read(self, request, queryset):
        queryset.update(is_read=True)
        self.message_user(request, "Les notifications sélectionnées ont été marquées comme lues.")
    mark_as_read.short_description = "Marquer comme Lu"

    def mark_as_unread(self, request, queryset):
        queryset.update(is_read=False)
        self.message_user(request, "Les notifications sélectionnées ont été marquées comme non lues.")
    mark_as_unread.short_description = "Marquer comme Non Lu"


# --- Monkey Patch default AdminSite.index to inject custom widgets statistics ---
original_index = admin.site.index

def custom_admin_index(request, extra_context=None):
    extra_context = extra_context or {}
    from core.models import PlantScan, SystemNotification
    import json
    from django.conf import settings
    from pathlib import Path
    
    # Scans counts
    scans = PlantScan.objects.all()
    total_scans = scans.count()
    healthy_scans = scans.filter(severity='healthy').count()
    warning_scans = scans.filter(severity='warning').count()
    critical_scans = scans.filter(severity='critical').count()
    
    # System notifications counts
    notifications = SystemNotification.objects.all().order_by('-created_at')
    unread_notifications = notifications.filter(is_read=False)
    unread_count = unread_notifications.count()
    unread_errors = unread_notifications.filter(type='error').count()
    
    # ESP32 settings config
    config_path = Path(settings.BASE_DIR) / 'esp32_config.json'
    config_data = {}
    if config_path.exists():
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
        except Exception:
            pass
            
    extra_context.update({
        'total_scans': total_scans,
        'healthy_scans': healthy_scans,
        'warning_scans': warning_scans,
        'critical_scans': critical_scans,
        'recent_scans': scans.order_by('-scanned_at')[:8],
        'recent_notifications': notifications[:8],
        'unread_count': unread_count,
        'unread_errors': unread_errors,
        'esp32_config': config_data,
    })
    return original_index(request, extra_context)

admin.site.index = custom_admin_index


# ─────────────────────────────────────────────────────────────────────────────
#  PHASE 2 — New model admins
# ─────────────────────────────────────────────────────────────────────────────

@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = ('scan', 'alert_type', 'short_message', 'is_read', 'created_at')
    list_filter = ('alert_type', 'is_read', 'created_at')
    search_fields = ('message', 'scan__disease_name')
    ordering = ('-created_at',)
    actions = ['mark_as_read']

    def short_message(self, obj):
        return obj.message[:80]
    short_message.short_description = "Message"

    def mark_as_read(self, request, queryset):
        queryset.update(is_read=True)
        self.message_user(request, f"{queryset.count()} alertes marquées comme lues.")
    mark_as_read.short_description = "Marquer comme lu"


@admin.register(SecurityLog)
class SecurityLogAdmin(admin.ModelAdmin):
    list_display = ('ip_address', 'endpoint', 'method', 'status_code', 'timestamp')
    list_filter = ('method', 'status_code', 'timestamp')
    search_fields = ('ip_address', 'endpoint')
    ordering = ('-timestamp',)
    readonly_fields = ('ip_address', 'endpoint', 'method', 'status_code', 'user_agent', 'timestamp')


@admin.register(BlockedIP)
class BlockedIPAdmin(admin.ModelAdmin):
    list_display = ('ip_address', 'reason', 'blocked_by', 'blocked_at')
    search_fields = ('ip_address', 'reason')
    ordering = ('-blocked_at',)


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ('week_start', 'week_end', 'total_scans', 'critical_count', 'healthy_count', 'created_at', 'download_link')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'total_scans', 'critical_count', 'warning_count', 'healthy_count')

    def download_link(self, obj):
        if obj.pdf_file:
            return format_html('<a href="{}" target="_blank">📄 Télécharger</a>', obj.pdf_file.url)
        return "—"
    download_link.short_description = "Rapport PDF"


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('session_id', 'role', 'short_message', 'language', 'created_at')
    list_filter = ('role', 'language', 'created_at')
    search_fields = ('message', 'session_id')
    ordering = ('-created_at',)

    def short_message(self, obj):
        return obj.message[:60]
    short_message.short_description = "Message"
