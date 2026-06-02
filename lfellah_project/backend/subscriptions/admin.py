from django.contrib import admin
from .models import Plan, Subscription


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'billing_cycle', 'price_mad', 'max_devices', 'is_active')
    list_filter = ('billing_cycle', 'is_active')
    search_fields = ('name', 'code')


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('user', 'plan', 'status', 'start_date', 'end_date', 'auto_renew')
    list_filter = ('status', 'plan', 'auto_renew')
    search_fields = ('user__email', 'plan__name')
    readonly_fields = ('start_date',)
