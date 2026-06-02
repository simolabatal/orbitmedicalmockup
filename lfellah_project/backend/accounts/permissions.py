"""
Permissions et décorateurs d'accès pour L'Fellah 2.0.
Gestion des 4 rôles distincts avec isolation stricte des sessions :
  - is_fellah_required   : Accès réservé aux vendeurs (Fellah).
  - is_saas_staff_required: Accès réservé au staff SaaS (Admin, Marketeur).
  - is_admin_required     : Accès réservé aux administrateurs système.
  - is_marketer_required  : Accès réservé à l'équipe marketing (lecture seule KPIs).
"""
from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import redirect
from functools import wraps


def is_fellah_required(view_func=None, redirect_url='/login/'):
    """
    Décorateur qui restreint l'accès aux utilisateurs avec le rôle 'farmer'.
    Les Fellahs sont les seuls à accéder au Dashboard Vendeur (CRUD produits).
    AUCUN accès aux données IoT des autres fermiers.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect(f'{redirect_url}?next={request.path}')
            if request.user.role != 'farmer':
                from django.shortcuts import render
                return render(request, 'core/error.html', {
                    'message': 'Cet espace est réservé aux Fellahs (Vendeurs/Coopératives). Contactez l\'administration pour ouvrir un compte vendeur.'
                }, status=403)
            # Vérifier le changement de mot de passe forcé
            if request.user.force_password_change:
                return redirect(f'/accounts/change-password/?force=true&next={request.path}')
            return view_func(request, *args, **kwargs)
        return _wrapped_view

    if view_func is None:
        return decorator
    return decorator(view_func)


def is_saas_staff_required(view_func=None, redirect_url='/login/'):
    """
    Décorateur qui restreint l'accès au staff SaaS (Admin + Marketeur).
    Utilisé pour le Dashboard SaaS (Exploitation IoT).
    Les Fellahs et Acheteurs n'ont pas accès à ces fonctionnalités.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect(f'{redirect_url}?next={request.path}')
            if request.user.role not in ('admin', 'marketer'):
                from django.shortcuts import render
                return render(request, 'core/error.html', {
                    'message': 'Accès réservé au personnel L\'Fellah. Cet espace n\'est pas accessible aux Fellahs ni aux Acheteurs.'
                }, status=403)
            if request.user.force_password_change:
                return redirect(f'/accounts/change-password/?force=true&next={request.path}')
            return view_func(request, *args, **kwargs)
        return _wrapped_view

    if view_func is None:
        return decorator
    return decorator(view_func)


def is_admin_required(view_func=None, redirect_url='/login/'):
    """
    Décorateur qui restreint l'accès aux administrateurs système uniquement.
    Utilisé pour : création de comptes SaaS, gestion des devices, supervision.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect(f'{redirect_url}?next={request.path}')
            if request.user.role != 'admin':
                from django.shortcuts import render
                return render(request, 'core/error.html', {
                    'message': 'Accès réservé aux Administrateurs Système.'
                }, status=403)
            return view_func(request, *args, **kwargs)
        return _wrapped_view

    if view_func is None:
        return decorator
    return decorator(view_func)


def is_marketer_required(view_func=None, redirect_url='/login/'):
    """
    Décorateur qui restreint l'accès à l'équipe marketing.
    Permet : consultation KPIs en lecture seule, gestion des codes promo.
    Interdit : modification des produits, accès IoT, création de comptes.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect(f'{redirect_url}?next={request.path}')
            if request.user.role not in ('marketer', 'admin'):
                from django.shortcuts import render
                return render(request, 'core/error.html', {
                    'message': 'Accès réservé à l\'équipe Marketing L\'Fellah.'
                }, status=403)
            return view_func(request, *args, **kwargs)
        return _wrapped_view

    if view_func is None:
        return decorator
    return decorator(view_func)
