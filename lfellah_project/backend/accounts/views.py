from rest_framework import viewsets, permissions, status, generics
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from django.contrib.auth import get_user_model, authenticate, login, logout
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
import uuid

from .models import PasswordResetToken
from .serializers import (
    UserSerializer, UserRegistrationSerializer,
    ChangePasswordSerializer, PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer,
)

User = get_user_model()


class UserViewSet(viewsets.ModelViewSet):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if self.request.user.role == 'admin':
            return User.objects.all()
        return User.objects.filter(id=self.request.user.id)

    def get_permissions(self):
        if self.action == 'create':
            return [permissions.AllowAny()]
        return super().get_permissions()

    def get_serializer_class(self):
        if self.action == 'create':
            return UserRegistrationSerializer
        return UserSerializer


class LoginView(generics.GenericAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = None

    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')
        user = authenticate(request, username=email, password=password)

        if user is None:
            return Response({'error': 'Email ou mot de passe incorrect.'}, status=401)
        if user.is_blocked:
            return Response({'error': 'Ce compte est bloqué. Contactez l\'administrateur.'}, status=403)

        login(request, user)
        return Response({
            'status': 'success',
            'user': UserSerializer(user).data,
            'force_password_change': user.force_password_change,
        })


class LogoutView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        logout(request)
        return Response({'status': 'logged_out'})


class ChangePasswordView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ChangePasswordSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user
        if not user.check_password(serializer.validated_data['old_password']):
            return Response({'error': 'Ancien mot de passe incorrect.'}, status=400)

        user.set_password(serializer.validated_data['new_password'])
        user.force_password_change = False
        user.save()
        return Response({'status': 'success', 'message': 'Mot de passe changé avec succès.'})


class PasswordResetRequestView(generics.GenericAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = PasswordResetRequestSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            user = User.objects.get(email=serializer.validated_data['email'])
        except User.DoesNotExist:
            # Ne pas révéler si l'email existe
            return Response({'status': 'success', 'message': 'Si cet email existe, un lien de réinitialisation a été envoyé.'})

        token = PasswordResetToken.objects.create(
            user=user,
            token=uuid.uuid4().hex,
            expires_at=timezone.now() + timezone.timedelta(hours=1),
        )

        reset_url = f"{request.build_absolute_uri('/')}reset-password/{token.token}/"
        send_mail(
            subject='L\'Fellah - Réinitialisation de mot de passe',
            message=f'Cliquez sur ce lien pour réinitialiser votre mot de passe : {reset_url}',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=True,
        )

        return Response({'status': 'success', 'message': 'Email de réinitialisation envoyé.'})


class PasswordResetConfirmView(generics.GenericAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = PasswordResetConfirmSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            token = PasswordResetToken.objects.get(
                token=serializer.validated_data['token'],
                is_used=False,
                expires_at__gt=timezone.now(),
            )
        except PasswordResetToken.DoesNotExist:
            return Response({'error': 'Token invalide ou expiré.'}, status=400)

        user = token.user
        user.set_password(serializer.validated_data['new_password'])
        user.save()

        token.is_used = True
        token.save()

        return Response({'status': 'success', 'message': 'Mot de passe réinitialisé avec succès.'})


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def toggle_user_block(request, user_id):
    if request.user.role != 'admin':
        return Response({'error': 'Permission refusée.'}, status=403)
    user = User.objects.get(id=user_id)
    user.is_blocked = not user.is_blocked
    user.save(update_fields=['is_blocked'])
    return Response({'status': 'success', 'is_blocked': user.is_blocked})
