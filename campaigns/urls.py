from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SubscriberViewSet, UnsubscribeView, CampaignViewSet

router = DefaultRouter()
router.register(r'subscribers', SubscriberViewSet, basename='subscriber')
router.register(r'campaigns', CampaignViewSet, basename='campaign')

urlpatterns = [
    path('api/', include(router.urls)),
    path('api/unsubscribe/', UnsubscribeView.as_view(), name='unsubscribe'),
]
