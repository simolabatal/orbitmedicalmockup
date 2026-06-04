from rest_framework import viewsets, permissions
from rest_framework.response import Response
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import login, authenticate, logout as auth_logout
from django.http import HttpResponse
from django.views import View

from .models import SecurityLog, BlockedIP
from .serializers import SecurityLogSerializer, BlockedIPSerializer
from .forms import VerifyCodeForm, ResetPasswordForm


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
        email = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password')
        password_confirm = request.POST.get('password_confirm')
        role = request.POST.get('role', 'farmer')
        phone = request.POST.get('phone', '')

        # Auto-generate username from email if not provided
        username = request.POST.get('username', '').strip()
        if not username:
            username = email.split('@')[0] if email else 'user'
        if not email:
            return render(request, 'core/register.html', {
                'error': 'Email requis.'
            })

        if password_confirm and password != password_confirm:
            return render(request, 'core/register.html', {
                'error': 'Les mots de passe ne correspondent pas.'
            })
        if not password or len(password) < 8:
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


# ─── PASSWORD RESET — 6-digit code ────────────────────────────────
import random
from django.core.cache import cache
from django.core.mail import send_mail
from django.conf import settings


def password_reset_request(request):
    """Envoie un code temporaire a 6 chiffres par email."""
    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
        from accounts.models import User
        user = User.objects.filter(email=email).first()

        if user:
            code = str(random.randint(100000, 999999))
            cache_key = f'pwd_reset_{email}'
            cache.set(cache_key, code, 900)  # 15 min TTL

            try:
                send_mail(
                    subject='L\'Fellah — Code de reinitialisation',
                    message=f'Votre code de reinitialisation est : {code}\n\n'
                            f'Ce code expire dans 15 minutes.\n\n'
                            f'Cordialement,\nL\'equipe L\'Fellah 2.0',
                    from_email=settings.DEFAULT_FROM_EMAIL or 'noreply@lfellah.ma',
                    recipient_list=[email],
                    fail_silently=True,
                )
                # Log: en dev, le backend console affichera l'email
                print(f'[PWD RESET] Code envoye a {email}: {code}')
            except Exception as e:
                print(f'[PWD RESET] Erreur email: {e}')

        # Toujours afficher la meme page (anti-enumeration)
        return render(request, 'core/registration/password_reset_done.html')

    return render(request, 'core/registration/password_reset_form.html')


class VerifyCodeView(View):
    """
    Verifie le code a 6 chiffres envoye par email.
    Si OK : request.session['email_verified'] = True + redirect vers ResetPasswordView.
    Le code temporaire est lu depuis le cache et JAMAIS stocke dans user.password.
    """

    def post(self, request):
        form = VerifyCodeForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email'].strip().lower()
            code = form.cleaned_data['code'].strip()
            cache_key = f'pwd_reset_{email}'
            stored_code = cache.get(cache_key)
            print(f'[PWD RESET] Verification — email={email} code_soumis={code} code_stocke={stored_code}')

            if not stored_code or str(stored_code) != str(code):
                print(f'[PWD RESET] ECHEC — code invalide ou expire pour {email}')
                return render(request, 'core/registration/password_reset_confirm.html', {
                    'error': 'Code invalide ou expire.',
                    'email': email,
                })

            # Code OK → autorise le changement de mot de passe via la session
            request.session['email_verified'] = True
            request.session['verified_email'] = email
            cache.delete(cache_key)  # le code ne sert plus
            return redirect('/password-reset/set-password/')

        return render(request, 'core/registration/password_reset_confirm.html', {'form': form})

    def get(self, request):
        return render(request, 'core/registration/password_reset_confirm.html')


class ResetPasswordView(View):
    """
    Vue de definition du nouveau mot de passe (Set Password).
    Recupere l'utilisateur par email, utilise user.set_password() puis user.save()
    pour garantir le hachage correct par Django. Le code temporaire n'est JAMAIS
    ecrit dans user.password.
    """

    def dispatch(self, request, *args, **kwargs):
        self.email = request.session.get('verified_email')
        self.verified = request.session.get('email_verified')
        if not self.email or not self.verified:
            return redirect('/password-reset/')
        return super().dispatch(request, *args, **kwargs)

    def post(self, request):
        from accounts.models import User
        try:
            user = User.objects.get(email=self.email)
        except User.DoesNotExist:
            request.session.pop('verified_email', None)
            request.session.pop('email_verified', None)
            return redirect('/password-reset/')

        print(f"[DEBUG RESET] user={user} | email={user.email} | active={user.is_active} | backend_attr={getattr(user, 'backend', 'N/A')}")
        form = ResetPasswordForm(request.POST)
        if form.is_valid():
            # Sécurité backend pour éviter toute ambiguïté de session/auth
            user.backend = 'django.contrib.auth.backends.ModelBackend'
            user.set_password(form.cleaned_data['password'])
            user.save()
            print(f"[DEBUG RESET] Password hash after save: {user.password[:30]}...")
            request.session.pop('verified_email', None)
            request.session.pop('email_verified', None)
            return render(request, 'core/registration/password_reset_complete.html')

        return render(request, 'core/registration/password_reset_set_password.html', {
            'form': form,
            'email': self.email,
        })

    def get(self, request):
        form = ResetPasswordForm()
        return render(request, 'core/registration/password_reset_set_password.html', {
            'form': form,
            'email': self.email,
        })
