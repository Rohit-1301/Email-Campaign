from django.core.management.base import BaseCommand
from django.utils import timezone
from campaigns.models import Campaign
from campaigns.services.dispatcher import dispatch_campaign

class Command(BaseCommand):
    help = 'Sends daily scheduled campaigns where published_date matches today'

    def handle(self, *args, **options):
        now = timezone.now()
        
        # Fetch campaigns where published_date is today and status is DRAFT/SCHEDULED
        # This matches the prompt requirement exactly.
        campaigns = Campaign.objects.filter(
            published_date__date=now.date(),
            status__in=[Campaign.Status.DRAFT, Campaign.Status.SCHEDULED]
        )

        if not campaigns.exists():
            self.stdout.write(self.style.SUCCESS("No campaigns matched for today's date."))
            return

        for campaign in campaigns:
            self.stdout.write(f"Initiating dispatch for campaign ID: {campaign.id} ({campaign.subject})...")
            success = dispatch_campaign(campaign.id)
            if success:
                self.stdout.write(self.style.SUCCESS(f"Campaign ID {campaign.id} dispatch completed."))
            else:
                self.stdout.write(self.style.ERROR(f"Campaign ID {campaign.id} dispatch rejected or failed."))
