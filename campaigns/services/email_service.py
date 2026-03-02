import smtplib
from typing import Tuple
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from campaigns.models import Campaign, Subscriber

def send_email_to_subscriber(campaign: Campaign, subscriber: Subscriber) -> Tuple[bool, str]:
    """
    Renders and sends an email via SMTP.
    If SMTP credentials are provided, attempts to send a real email.
    Otherwise, simulates success.
    
    Returns a tuple (success_boolean, response_message_string).
    """
    try:
        # Render HTML content using django template
        html_content = render_to_string('base_email.html', {
            'subscriber': subscriber,
            'campaign': campaign,
            'article_url': campaign.article_url,
            'html_content': campaign.html_content,    # Raw user HTML / rich text
            'preview_text': campaign.preview_text,
            'subject': campaign.subject,
            # We assume your domain base is configured or handle relative urls in template
        })

        if settings.EMAIL_HOST_USER and settings.EMAIL_HOST_PASSWORD:
            email = EmailMultiAlternatives(
                subject=campaign.subject,
                body=campaign.plain_text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[subscriber.email],
            )
            email.attach_alternative(html_content, "text/html")
            email.send(fail_silently=False)
            return True, "Email sent successfully"
        else:
            # Simulate success if no credentials specified (for development/testing)
            return True, "Simulated success (no SMTP credentials configured)"

    except smtplib.SMTPException as e:
        return False, f"SMTP Error: {str(e)}"
    except Exception as e:
        return False, f"Unexpected Error: {str(e)}"
