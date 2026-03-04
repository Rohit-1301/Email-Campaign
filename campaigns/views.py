from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.decorators import action
from .models import Subscriber, Campaign
from .serializers import SubscriberSerializer, UnsubscribeSerializer, CampaignSerializer
from .services.dispatcher import dispatch_campaign

class SubscriberViewSet(viewsets.ModelViewSet):
    """
    Provides endpoints for Subscriber creation and management.
    Handles POST /api/subscribers/
    """
    queryset = Subscriber.objects.all()
    serializer_class = SubscriberSerializer


class UnsubscribeView(APIView):
    """
    Endpoint dedicated exclusively to unsubscribe functionality.
    Handles POST /api/unsubscribe/
    """
    def get(self, request, *args, **kwargs):
        email = request.query_params.get('email')
        if not email:
            return Response({"detail": "Email parameter is required."}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            subscriber = Subscriber.objects.get(email=email)
        except Subscriber.DoesNotExist:
            return Response({"detail": "Subscriber not found."}, status=status.HTTP_404_NOT_FOUND)
            
        subscriber.is_active = False
        subscriber.unsubscribed_at = timezone.now()
        subscriber.save(update_fields=['is_active', 'unsubscribed_at'])
        
        return Response({"detail": f"Successfully unsubscribed {email}."}, status=status.HTTP_200_OK)

    def post(self, request, *args, **kwargs):
        serializer = UnsubscribeSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            subscriber = Subscriber.objects.get(email=email)
            
            subscriber.is_active = False
            subscriber.unsubscribed_at = timezone.now()
            subscriber.save(update_fields=['is_active', 'unsubscribed_at'])
            
            return Response({"detail": "Successfully unsubscribed."}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CampaignViewSet(viewsets.ModelViewSet):
    """
    Provides endpoints for Campaign creation and management.
    Covers POST /api/campaigns/
    """
    queryset = Campaign.objects.all()
    serializer_class = CampaignSerializer

    @action(detail=True, methods=['post'], url_path='send')
    def send_campaign(self, request, pk=None):
        """
        Custom endpoint: POST /api/campaigns/<id>/send/
        Delegates the logic to the service layer (dispatch_campaign).
        """
        success = dispatch_campaign(pk)
        if success:
            return Response({"detail": "Campaign dispatch successful or in progress depending on wait context."}, status=status.HTTP_200_OK)
        return Response({"detail": "Campaign dispatch rejected (invalid status or locking error)."}, status=status.HTTP_400_BAD_REQUEST)
