import logging
import queue
import threading
from django.db import transaction
from django.utils import timezone
from campaigns.models import Campaign, Subscriber, EmailLog
from .email_service import send_email_to_subscriber

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────
# PUB-SUB IMPLEMENTATION
# Publisher  → puts email jobs onto a thread-safe Queue
# Subscribers → worker threads that consume jobs from Queue
# ─────────────────────────────────────────────────────────

NUM_WORKER_THREADS = 10
_SENTINEL = None  # Poison pill to signal workers to stop


def _subscriber_worker(job_queue: queue.Queue) -> None:
    """
    Subscriber worker thread.
    Continuously pulls (campaign, subscriber, email_log) jobs 
    from the shared queue and processes them until it receives
    the SENTINEL (None) poison pill to stop.
    """
    while True:
        job = job_queue.get()

        # Poison pill — signal to shut down this worker thread
        if job is _SENTINEL:
            job_queue.task_done()
            break

        campaign, subscriber, email_log = job
        try:
            success, message = send_email_to_subscriber(campaign, subscriber)
            email_log.status = EmailLog.Status.SENT if success else EmailLog.Status.FAILED
            email_log.response_message = message
            email_log.sent_at = timezone.now() if success else None
            email_log.save(update_fields=['status', 'response_message', 'sent_at'])
            logger.info(f"[Worker] Email to {subscriber.email}: {'SENT' if success else 'FAILED'}")
        except Exception as e:
            logger.error(f"[Worker] Exception for {subscriber.email}: {str(e)}")
            email_log.status = EmailLog.Status.FAILED
            email_log.response_message = f"Thread exception: {str(e)}"
            email_log.save(update_fields=['status', 'response_message'])
        finally:
            job_queue.task_done()


def _publisher(job_queue: queue.Queue, campaign: Campaign, pending_logs) -> None:
    """
    Publisher function.
    Iterates over pending EmailLog records and publishes 
    (campaign, subscriber, log) job tuples onto the shared Queue.
    After publishing all jobs, sends NUM_WORKER_THREADS sentinel
    values to gracefully shut down all worker threads.
    """
    for log in pending_logs:
        job_queue.put((campaign, log.subscriber, log))
        logger.debug(f"[Publisher] Queued email job for {log.subscriber.email}")

    # Send one sentinel per worker to shut them all down
    for _ in range(NUM_WORKER_THREADS):
        job_queue.put(_SENTINEL)


def dispatch_campaign(campaign_id: int) -> bool:
    """
    Main dispatcher using Pub-Sub pattern with Python queue.Queue.

    Flow:
      1. Acquire row-level lock via select_for_update inside transaction.atomic()
      2. Validate campaign status (must be DRAFT or SCHEDULED)
      3. Update status → SENDING and commit
      4. Bulk create EmailLog entries (PENDING)
      5. Publisher thread pushes jobs onto Queue
      6. NUM_WORKER_THREADS subscriber threads consume and send emails
      7. After all workers finish → update campaign status → SENT

    Returns True if successfully dispatched, False otherwise.
    """
    # Step 1-3: Row-level lock + status validation
    try:
        with transaction.atomic():
            campaign = Campaign.objects.select_for_update().get(id=campaign_id)

            if campaign.status not in [Campaign.Status.DRAFT, Campaign.Status.SCHEDULED]:
                logger.warning(
                    f"Campaign {campaign_id} cannot be sent. Current status: {campaign.status}"
                )
                return False

            campaign.status = Campaign.Status.SENDING
            campaign.save(update_fields=['status'])

    except Campaign.DoesNotExist:
        logger.error(f"Campaign {campaign_id} does not exist.")
        return False
    except Exception as e:
        logger.error(f"Lock error for campaign {campaign_id}: {str(e)}")
        return False

    # Step 4: Fetch active subscribers and bulk create PENDING EmailLog entries
    active_subscribers = Subscriber.objects.filter(is_active=True)

    # Avoid duplicates if logs already exist for this campaign
    existing_ids = set(
        EmailLog.objects.filter(campaign=campaign).values_list('subscriber_id', flat=True)
    )

    new_logs = []
    for sub in active_subscribers:
        if sub.id not in existing_ids:
            new_logs.append(EmailLog(campaign=campaign, subscriber=sub, status=EmailLog.Status.PENDING))
        if len(new_logs) == 500:
            EmailLog.objects.bulk_create(new_logs)
            new_logs = []
    if new_logs:
        EmailLog.objects.bulk_create(new_logs)

    # Fetch all pending logs with subscriber info
    pending_logs = list(
        EmailLog.objects.filter(campaign=campaign, status=EmailLog.Status.PENDING)
        .select_related('subscriber')
    )

    if not pending_logs:
        logger.info(f"No pending subscribers for campaign {campaign_id}.")
        campaign.status = Campaign.Status.SENT
        campaign.save(update_fields=['status'])
        return True

    # Step 5-6: Pub-Sub — shared Queue, publisher thread + subscriber worker threads
    job_queue: queue.Queue = queue.Queue(maxsize=0)  # Unbounded queue

    # Start subscriber worker threads FIRST (they wait for jobs)
    workers = []
    for i in range(NUM_WORKER_THREADS):
        t = threading.Thread(target=_subscriber_worker, args=(job_queue,), daemon=True)
        t.start()
        workers.append(t)
        logger.debug(f"[PubSub] Worker thread {i+1} started.")

    # Publisher thread pushes all jobs onto the queue
    publisher_thread = threading.Thread(
        target=_publisher, args=(job_queue, campaign, pending_logs), daemon=True
    )
    publisher_thread.start()
    logger.info(f"[PubSub] Publisher started for campaign {campaign_id} with {len(pending_logs)} jobs.")

    # Wait for publisher to finish (30s timeout)
    publisher_thread.join(timeout=30)

    # Wait for all jobs to be consumed from the queue
    job_queue.join()

    # Wait for all worker threads to terminate (30s timeout each)
    for t in workers:
        t.join(timeout=30)

    logger.info(f"[PubSub] All workers done for campaign {campaign_id}.")

    # Step 7: Mark campaign as SENT
    campaign.status = Campaign.Status.SENT
    campaign.save(update_fields=['status'])

    return True
