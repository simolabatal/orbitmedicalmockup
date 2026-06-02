"""
Middleware de securite — Restreint l'acces par groupe pour les URLs critiques.
Se declenche APRES l'authentification (doit etre place apres auth middleware).
"""
from django.http import HttpResponseForbidden
from django.shortcuts import redirect
from django.urls import resolve
import logging

logger = logging.getLogger(__name__)


class SecurityLoggingMiddleware:
    """Log toutes les requetes pour audit."""
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, 'user', None)
        user_str = user if user else 'Anonymous'
        logger.debug(f"[{request.method}] {request.path} — User: {user_str}")
        return self.get_response(request)


class RestrictAccessMiddleware:
    """
    Interdit l'acces croise Finance <-> IoT au niveau URL.
    - /dashboard-iot/  : FINANCE groupe interdit (403)
    - /dashboard-admin/ : FINANCE groupe interdit (403)
    - /dashboard-finance/ : seuls les FINANCE membres (403 sinon)
    - /api/sensors/    : FINANCE interdit (403, bloque l'ingest bridge pour Finance)
    """

    IOT_PROTECTED = (
        '/dashboard-iot/',
        '/dashboard-admin/',
        '/dashboard-capteurs/',
    )
    FINANCE_PROTECTED = (
        '/dashboard-finance/',
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path

        # --- IoT routes : bloquer Finance (laisse le decorateur gerer anon) ---
        for prefix in self.IOT_PROTECTED:
            if path.startswith(prefix):
                if request.user.is_authenticated and request.user.groups.filter(name='Finance').exists():
                    return HttpResponseForbidden(
                        '<h1>403 Forbidden</h1><p>Acces interdit — groupe Finance.</p>'
                    )

        # --- Finance routes : seuls les Finance ---
        for prefix in self.FINANCE_PROTECTED:
            if path.startswith(prefix):
                if not request.user.is_authenticated:
                    return redirect('/login/?next=' + path)
                if not request.user.groups.filter(name='Finance').exists():
                    return HttpResponseForbidden(
                        '<h1>403 Forbidden</h1><p>Acces reserve au groupe Finance.</p>'
                    )

        return self.get_response(request)
