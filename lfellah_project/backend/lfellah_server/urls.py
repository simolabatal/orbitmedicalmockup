from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import FileResponse, HttpResponse
import os


def serve_sw(request):
    sw_path = os.path.join(settings.BASE_DIR, 'core', 'static', 'api', 'sw.js')
    return FileResponse(open(sw_path, 'rb'), content_type='application/javascript')


def serve_manifest(request):
    manifest_path = os.path.join(settings.BASE_DIR, 'core', 'static', 'api', 'manifest.json')
    return FileResponse(open(manifest_path, 'rb'), content_type='application/manifest+json')


urlpatterns = [
    path('admin/', admin.site.urls),
    path('sw.js', serve_sw, name='service-worker'),
    path('manifest.json', serve_manifest, name='manifest'),
    # Dashboard et API (core inclut capteurs + scans)
    path('', include('apps.dashboard.urls')),
    path('', include('core.urls')),
    # Marketplace
    path('', include('marketplace.urls')),
    # Autres apps
    path('', include('accounts.urls')),
    path('', include('subscriptions.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
