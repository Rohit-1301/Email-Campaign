from django.db import models
from django.utils.translation import gettext_lazy as _

class Subscriber(models.Model):
    """
    Subscribers model representing users who receive campaigns.
    Uses soft delete logic via `is_active` instead of hard deletion.
    """
    email = models.EmailField(unique=True, db_index=True)
    first_name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    unsubscribed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.email


class Campaign(models.Model):
    """
    Campaigns to be sent to active subscribers.
    """
    class Status(models.TextChoices):
        DRAFT = 'DRAFT', _('Draft')
        SCHEDULED = 'SCHEDULED', _('Scheduled')
        SENDING = 'SENDING', _('Sending')
        SENT = 'SENT', _('Sent')

    subject = models.CharField(max_length=255)
    preview_text = models.CharField(max_length=255)
    article_url = models.URLField()
    html_content = models.TextField()
    plain_text_content = models.TextField()
    published_date = models.DateTimeField(help_text=_("When the campaign should be publicly available / sent"))
    status = models.CharField(
        max_length=20, 
        choices=Status.choices, 
        default=Status.DRAFT
    )

    class Meta:
        ordering = ['-published_date']

    def __str__(self) -> str:
        return self.subject


class EmailLog(models.Model):
    """
    Intermediate many-to-many model tracking delivery statuses 
    for each subscriber per campaign.
    """
    class Status(models.TextChoices):
        PENDING = 'PENDING', _('Pending')
        SENT = 'SENT', _('Sent')
        FAILED = 'FAILED', _('Failed')

    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name="email_logs")
    subscriber = models.ForeignKey(Subscriber, on_delete=models.CASCADE, related_name="email_logs")
    status = models.CharField(
        max_length=20, 
        choices=Status.choices, 
        default=Status.PENDING
    )
    response_message = models.TextField(blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['campaign', 'subscriber'], name='unique_campaign_subscriber')
        ]
        indexes = [
            models.Index(fields=['campaign']),
            models.Index(fields=['subscriber']),
            models.Index(fields=['status']),
        ]

    def __str__(self) -> str:
        return f"{self.campaign.subject} -> {self.subscriber.email} ({self.status})"
