from django.contrib import admin
from .models import Subscriber, Campaign, EmailLog

@admin.register(Subscriber)
class SubscriberAdmin(admin.ModelAdmin):
    list_display = ('email', 'first_name', 'is_active', 'unsubscribed_at', 'created_at')
    search_fields = ('email', 'first_name')
    list_filter = ('is_active',)


@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = ('subject', 'status', 'published_date')
    list_filter = ('status',)
    search_fields = ('subject',)
    ordering = ('-published_date',)


@admin.register(EmailLog)
class EmailLogAdmin(admin.ModelAdmin):
    list_display = ('campaign', 'subscriber', 'status', 'sent_at')
    list_filter = ('status',)
    search_fields = ('subscriber__email', 'campaign__subject')
