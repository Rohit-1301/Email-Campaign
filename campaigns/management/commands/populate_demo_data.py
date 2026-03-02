from django.core.management.base import BaseCommand
from django.utils import timezone
from campaigns.models import Subscriber, Campaign

class Command(BaseCommand):
    help = 'Populates the database with demo data (subscribers and campaigns).'

    def handle(self, *args, **options):
        self.stdout.write("Creating demo data...")

        # Create demo subscribers
        subscribers_data = [
            {"email": "alice@example.com", "first_name": "Alice", "is_active": True},
            {"email": "bob@example.com", "first_name": "Bob", "is_active": True},
            {"email": "charlie@example.com", "first_name": "Charlie", "is_active": True},
            {"email": "david@example.com", "first_name": "David", "is_active": False}, # Unsubscribed user
            {"email": "eve@example.com", "first_name": "Eve", "is_active": True},
        ]
        
        subs_created = 0
        for sub_data in subscribers_data:
            if not Subscriber.objects.filter(email=sub_data['email']).exists():
                Subscriber.objects.create(**sub_data)
                subs_created += 1

        self.stdout.write(self.style.SUCCESS(f"Created {subs_created} new subscribers."))

        # Create demo campaigns
        now = timezone.now()
        campaigns_data = [
            {
                "subject": "🚀 Welcome to our New Platform!",
                "preview_text": "Check out all the new features we just released.",
                "article_url": "https://example.com/blog/new-platform-release",
                "html_content": "<p>We are thrilled to announce our brand new platform update!</p><p>We highly recommend you read our latest article covering all changes.</p><ul><li>Faster</li><li>More Secure</li><li>Sleeker Design</li></ul>",
                "plain_text_content": "We are thrilled to announce our brand new platform update!\n\Read all about it here: https://example.com/blog/new-platform-release",
                "published_date": now, # Set to right now so we can test the dispatcher
                "status": Campaign.Status.DRAFT,
            },
            {
                "subject": "📅 Don't miss our Webinar next week!",
                "preview_text": "Learn about the future of AI in our exclusive webinar.",
                "article_url": "https://example.com/events/ai-webinar",
                "html_content": "<p>Join us next Thursday for an exclusive webinar on <b>The Future of AI</b>.</p><p>Our industry experts will discuss upcoming trends and what you need to prepare for.</p>",
                "plain_text_content": "Join us next Thursday for an exclusive webinar on the Future of AI.\n\nReserve your spot: https://example.com/events/ai-webinar",
                "published_date": now + timezone.timedelta(days=7), # Future campaign
                "status": Campaign.Status.SCHEDULED,
            }
        ]

        camps_created = 0
        for camp_data in campaigns_data:
            if not Campaign.objects.filter(subject=camp_data['subject']).exists():
                Campaign.objects.create(**camp_data)
                camps_created += 1
                
        self.stdout.write(self.style.SUCCESS(f"Created {camps_created} new campaigns."))
        self.stdout.write(self.style.SUCCESS("Demo data populated successfully!"))
