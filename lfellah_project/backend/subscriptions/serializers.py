from rest_framework import serializers
from .models import Plan, Subscription


class PlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = Plan
        fields = [
            'id', 'name', 'code', 'description', 'billing_cycle',
            'price_mad', 'max_devices', 'max_scans_per_day',
            'max_products', 'includes_ai_chatbot',
            'includes_pdf_reports', 'includes_marketplace',
            'includes_iot_control', 'is_active',
        ]


class SubscriptionSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    plan_name = serializers.CharField(source='plan.name', read_only=True)
    is_active = serializers.SerializerMethodField()

    class Meta:
        model = Subscription
        fields = [
            'id', 'user', 'user_email', 'plan', 'plan_name',
            'status', 'start_date', 'end_date', 'auto_renew',
            'payment_method', 'last_payment_date',
            'is_active', 'created_at', 'updated_at',
        ]
        read_only_fields = [
            'user', 'start_date', 'last_payment_date',
            'created_at', 'updated_at',
        ]

    def get_is_active(self, obj):
        return obj.is_active_subscription


class SubscribeSerializer(serializers.Serializer):
    plan_id = serializers.IntegerField()
    payment_method = serializers.CharField(max_length=50, required=False, default='stripe')
