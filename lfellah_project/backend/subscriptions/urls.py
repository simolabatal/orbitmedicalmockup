from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'plans', views.PlanViewSet, basename='plans')
router.register(r'', views.SubscriptionViewSet, basename='subscriptions')

urlpatterns = [
    path('api/subscriptions/', include(router.urls)),
]
