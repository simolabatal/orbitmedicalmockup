from rest_framework import viewsets, permissions
from rest_framework.response import Response
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import login, authenticate, logout as auth_logout
from django.http import HttpResponse

from .models import SecurityLog, BlockedIP
from .serializers import SecurityLogSerializer, BlockedIPSerializer


def is_saas_staff(user):
    return user.is_authenticated and user.role in ('admin', 'agronomist')


def is_finance_staff(user):
    """Acces strictement au groupe Finance."""
    return user.is_authenticated and user.groups.filter(name='Finance').exists()


def is_iot_staff(user):
    """Acces strictement NON Finance (Admin/Agronome)."""
    if not user.is_authenticated:
        return False
    if user.groups.filter(name='Finance').exists():
        return False
    return user.role in ('admin', 'agronomist')


class IsIotStaff(permissions.BasePermission):
    """DRF Permission : acces reserve aux utilisateurs IoT (non-Finance)."""
    def has_permission(self, request, view):
        return is_iot_staff(request.user)


class SecurityLogViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = SecurityLogSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if self.request.user.role != 'admin':
            return SecurityLog.objects.none()
        return SecurityLog.objects.order_by('-timestamp')[:200]


class BlockedIPViewSet(viewsets.ModelViewSet):
    serializer_class = BlockedIPSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if self.request.user.role != 'admin':
            return BlockedIP.objects.none()
        return BlockedIP.objects.all()

    def perform_create(self, serializer):
        serializer.save(blocked_by=self.request.user)


def login_page(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        user = authenticate(request, username=email, password=password)
        if user is not None:
            if user.is_blocked:
                return render(request, 'core/login.html', {
                    'error': 'Ce compte est bloqu\u00e9. Contactez l\'administrateur.'
                })
            login(request, user)
            if user.force_password_change:
                return redirect('/accounts/change-password/?force=true')
            next_url = request.GET.get('next', '')
            if next_url and next_url.startswith('/'):
                return redirect(next_url)
            if user.groups.filter(name='Finance').exists():
                return redirect('/dashboard-finance/')
            ROLE_REDIRECT = {
                'farmer': '/vendeur/dashboard/',
                'admin': '/dashboard-iot/',
                'agronomist': '/dashboard-iot/',
                'marketer': '/marketing/',
                'buyer': '/',
            }
            return redirect(ROLE_REDIRECT.get(user.role, '/'))

        return render(request, 'core/login.html', {
            'error': 'Email ou mot de passe incorrect.'
        })
    return render(request, 'core/login.html')


def register_page(request):
    if request.method == 'POST':
        from accounts.models import User
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        password_confirm = request.POST.get('password_confirm')
        role = request.POST.get('role', 'farmer')
        phone = request.POST.get('phone', '')

        if password != password_confirm:
            return render(request, 'core/register.html', {
                'error': 'Les mots de passe ne correspondent pas.'
            })
        if len(password) < 8:
            return render(request, 'core/register.html', {
                'error': 'Le mot de passe doit contenir au moins 8 caract\u00e8res.'
            })
        if User.objects.filter(email=email).exists():
            return render(request, 'core/register.html', {
                'error': 'Cet email est d\u00e9j\u00e0 utilis\u00e9.'
            })
        if User.objects.filter(username=username).exists():
            return render(request, 'core/register.html', {
                'error': 'Ce nom d\'utilisateur est d\u00e9j\u00e0 pris.'
            })

        user = User.objects.create_user(username=username, email=email, password=password)
        user.role = role
        user.phone = phone
        user.force_password_change = (role == 'farmer')
        user.save()

        login(request, user)
        if role == 'farmer':
            return redirect('/dashboard/')
        return redirect('/')

    return render(request, 'core/register.html')


def change_password_page(request):
    if not request.user.is_authenticated:
        return redirect('/login/')

    if request.method == 'POST':
        old_password = request.POST.get('old_password')
        new_password = request.POST.get('new_password')
        new_password_confirm = request.POST.get('new_password_confirm')

        if new_password != new_password_confirm:
            return render(request, 'core/change_password.html', {
                'error': 'Les mots de passe ne correspondent pas.'
            })
        if not request.user.check_password(old_password):
            return render(request, 'core/change_password.html', {
                'error': 'Ancien mot de passe incorrect.'
            })

        request.user.set_password(new_password)
        request.user.force_password_change = False
        request.user.save()
        from django.contrib.auth import update_session_auth_hash
        update_session_auth_hash(request, request.user)
        return redirect('/dashboard/')

    return render(request, 'core/change_password.html')


def logout_page(request):
    auth_logout(request)
    return redirect('/')
