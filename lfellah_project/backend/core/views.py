# Split refactor shim — imports everything from focused submodules so existing URL imports don't break
from .views_auth import *
from .views_sensors import *
from .views_plants import *
from .views_finance import *
from .views_chatbot import *

# ─── DEBUG ROUTE LIST ─────────────────────────────────────────────
# Expose toutes les URLs enregistrees en JSON pour diagnostic runtime
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from django.urls import get_resolver


@api_view(['GET'])
@permission_classes([AllowAny])
def debug_routes(request):
    resolver = get_resolver()
    routes = []
    def collect(pattern, prefix=''):
        if hasattr(pattern, 'url_patterns'):
            for p in pattern.url_patterns:
                collect(p, prefix + str(pattern.pattern))
        else:
            routes.append({
                'route': prefix + str(pattern.pattern),
                'name': getattr(pattern, 'name', ''),
            })
    collect(resolver)
    return Response({
        'count': len(routes),
        'routes': sorted(routes, key=lambda x: x['route']),
        'requested_url': request.build_absolute_uri(),
        'settings_module': __import__('os').environ.get('DJANGO_SETTINGS_MODULE'),
    })
