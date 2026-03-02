from rest_framework import serializers
from .models import Subscriber, Campaign

class SubscriberSerializer(serializers.ModelSerializer):
    """
    Serializer to handle Subscriber creation and retrieval.
    Fields like is_active, unsubscribed_at, etc., are read-only
    to prevent manual overriding during creation.
    """
    class Meta:
        model = Subscriber
        fields = ['id', 'email', 'first_name', 'is_active', 'unsubscribed_at', 'created_at', 'updated_at']
        read_only_fields = ['is_active', 'unsubscribed_at', 'created_at', 'updated_at']


class UnsubscribeSerializer(serializers.Serializer):
    """
    Serializer for the unsubscribe endpoint.
    Validates that the provided email exists.
    """
    email = serializers.EmailField()

    def validate_email(self, value: str) -> str:
        if not Subscriber.objects.filter(email=value).exists():
            raise serializers.ValidationError("Subscriber with this email does not exist.")
        return value


class CampaignSerializer(serializers.ModelSerializer):
    """
    Serializer to handle Campaign creation and partial updates.
    Status is managed internally / via the dispatcher, so it's read-only.
    """
    class Meta:
        model = Campaign
        fields = [
            'id', 'subject', 'preview_text', 'article_url', 
            'html_content', 'plain_text_content', 'published_date', 'status'
        ]
        read_only_fields = ['status']
