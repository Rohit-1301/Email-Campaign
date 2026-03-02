import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from django.db import transaction
from django.utils import timezone
from campaigns.models import Campaign, Subscriber, EmailLog
from .email_service import send_email_to_subscriber

logger = logging.getLogger(__name__)

def process_single_email(campaign: Campaign, subscriber: Subscriber, email_log: EmailLog) -> None:
    """
    Renders email template, sends via SMTP, and updates its own EmailLog row.
    Intended to be executed in a thread pool. Catches all exceptions.
    """
    try:
        success, message = send_email_to_subscriber(campaign, subscriber)
        email_log.status = EmailLog.Status.SENT if success else EmailLog.Status.FAILED
        email_log.response_message = message
        email_log.sent_at = timezone.now() if success else None
        email_log.save(update_fields=['status', 'response_message', 'sent_at'])
    except Exception as e:
        logger.error(f"Unforeseen thread error for {subscriber.email}: {str(e)}")
        email_log.status = EmailLog.Status.FAILED
        email_log.response_message = f"Thread exception: {str(e)}"
        email_log.save(update_fields=['status', 'response_message'])


def dispatch_campaign(campaign_id: int) -> bool:
    """
    Handles race conditions via transaction.atomic + select_for_update.
    Batches active subscribers, creates EmailLogs, and utilizes ThreadPoolExecutor(10) to dispatch.
    Returns True if successfully sent, False otherwise.
    """
    # 1. atomic() for acquiring row lock
    try:
        with transaction.atomic():
            # 2. select_for_update() prevents concurrent task triggers
            campaign = Campaign.objects.select_for_update().get(id=campaign_id)
            
            # 3. If status not DRAFT/SCHEDULED -> reject
            if campaign.status not in [Campaign.Status.DRAFT, Campaign.Status.SCHEDULED]:
                logger.warning(f"Campaign {campaign_id} cannot be sent. Current status: {campaign.status}")
                return False

            # 4. Update status -> SENDING & 5. Commit via ending atomic context
            campaign.status = Campaign.Status.SENDING
            campaign.save(update_fields=['status'])
            
    except Campaign.DoesNotExist:
        logger.error(f"Failed to lock: Campaign {campaign_id} does not exist.")
        return False
    except Exception as e:
        logger.error(f"Database lock error for campaign {campaign_id}: {str(e)}")
        return False

    # 6. Fetch active subscribers
    subscribers = Subscriber.objects.filter(is_active=True).iterator()

    # 7. Bulk create EmailLog entries as PENDING safely avoiding constraint issues
    existing_subscriber_ids = set(EmailLog.objects.filter(
        campaign=campaign
    ).values_list('subscriber_id', flat=True))

    logs_created = []
    # Using batches to avoid loading all into memory at once if big lists
    for sub in subscribers:
        if sub.id not in existing_subscriber_ids:
            logs_created.append(
                EmailLog(campaign=campaign, subscriber=sub, status=EmailLog.Status.PENDING)
            )
            
            # Flush batch every 500 records
            if len(logs_created) == 500:
                EmailLog.objects.bulk_create(logs_created)
                logs_created = []

    if logs_created:
        EmailLog.objects.bulk_create(logs_created)
    
    # 8-9. Retrieve pending logs and Dispatch emails using max_workers=10
    pending_logs = EmailLog.objects.filter(
        campaign=campaign, status=EmailLog.Status.PENDING
    ).select_related('subscriber')

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = []
        for log in pending_logs:
            futures.append(
                executor.submit(process_single_email, campaign, log.subscriber, log)
            )

        # Wait until everything finishes
        for future in as_completed(futures):
            try:
                future.result()  # Not returning anything, but handles propagation if omitted inside thread
            except Exception as e:
                # Do not crash the entire pool if one task has critical unhandled failure
                logger.error(f"Pool future returned an exception: {str(e)}")

    # 10. After completion -> update campaign status -> SENT
    campaign.status = Campaign.Status.SENT
    campaign.save(update_fields=['status'])

    return True
