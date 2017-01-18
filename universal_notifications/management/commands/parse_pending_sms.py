# -*- coding: utf-8 -*-
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils.timezone import now
from universal_notifications.backends.twilio.tasks import parse_received_message_task
from universal_notifications.models import PhoneReceivedRaw


class Command(BaseCommand):
    args = ''
    help = 'Check if message parsed'

    def handle(self, *args, **options):
        # TODO: configurable? Now user needs to remember to run it every minute via cron
        # maybe there should be some cron file created for UN by default?
        # or maybe "ago" should be simply removed?
        ago = now() - timedelta(minutes=1)
        raws = PhoneReceivedRaw.objects.filter(status=PhoneReceivedRaw.STATUS_PENDING, created__lte=ago)
        for raw in raws:
            parse_received_message_task(raw.id)
