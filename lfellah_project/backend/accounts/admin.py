from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, PasswordResetToken


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('email', 'username', 'role', 'phone', 'region', 'is_blocked', 'email_verified', 'date_joined')
    list_filter = ('role', 'is_blocked', 'email_verified', 'date_joined')
    search_fields = ('email', 'username', 'phone')
    ordering = ('-date_joined',)
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Profil L\'Fellah', {'fields': ('role', 'phone', 'region', 'preferred_language', 'is_blocked', 'force_password_change', 'email_verified')}),
    )


@admin.register(PasswordResetToken)
class PasswordResetTokenAdmin(admin.ModelAdmin):
    list_display = ('user', 'token', 'expires_at', 'is_used', 'created_at')
    list_filter = ('is_used',)
    readonly_fields = ('token', 'created_at')
