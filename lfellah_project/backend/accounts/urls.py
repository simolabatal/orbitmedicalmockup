from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'users', views.UserViewSet, basename='users')

urlpatterns = [
    path('api/accounts/', include(router.urls)),
    path('api/accounts/register/', views.UserViewSet.as_view({'post': 'create'}), name='register'),
    path('api/accounts/login/', views.LoginView.as_view(), name='login'),
    path('api/accounts/logout/', views.LogoutView.as_view(), name='logout'),
    path('api/accounts/change-password/', views.ChangePasswordView.as_view(), name='change-password'),
    path('api/accounts/reset-password/', views.PasswordResetRequestView.as_view(), name='reset-password-request'),
    path('api/accounts/reset-password/confirm/', views.PasswordResetConfirmView.as_view(), name='reset-password-confirm'),
    path('api/accounts/users/<int:user_id>/toggle-block/', views.toggle_user_block, name='toggle-user-block'),
]
