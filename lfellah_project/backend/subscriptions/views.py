from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes, action
from django.utils import timezone
from dateutil.relativedelta import relativedelta

from .models import Plan, Subscription
from .serializers import PlanSerializer, SubscriptionSerializer, SubscribeSerializer


class PlanViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Plan.objects.filter(is_active=True).order_by('price_mad')
    serializer_class = PlanSerializer
    permission_classes = [permissions.AllowAny]


class SubscriptionViewSet(viewsets.ModelViewSet):
    serializer_class = SubscriptionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Subscription.objects.select_related('plan').filter(
            user=self.request.user
        ).order_by('-created_at')

    @action(methods=['POST'], detail=False, url_path='subscribe')
    def subscribe(self, request):
        serializer = SubscribeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        plan = Plan.objects.get(id=serializer.validated_data['plan_id'], is_active=True)

        Subscription.objects.filter(user=request.user, status='active').update(status='cancelled')

        if plan.billing_cycle == 'monthly':
            end_date = timezone.now() + relativedelta(months=1)
        else:
            end_date = timezone.now() + relativedelta(years=1)

        subscription = Subscription.objects.create(
            user=request.user,
            plan=plan,
            end_date=end_date,
            payment_method=serializer.validated_data.get('payment_method', 'stripe'),
            last_payment_date=timezone.now(),
        )

        return Response(SubscriptionSerializer(subscription).data, status=status.HTTP_201_CREATED)

    @action(methods=['POST'], detail=True, url_path='cancel')
    def cancel(self, request, pk=None):
        subscription = self.get_object()
        subscription.status = 'cancelled'
        subscription.auto_renew = False
        subscription.save(update_fields=['status', 'auto_renew'])
        return Response({'status': 'cancelled'})
