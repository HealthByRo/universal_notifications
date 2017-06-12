# -*- coding: utf-8 -*-
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils.timezone import now
from universal_notifications.models import PhoneReceivedRaw
from universal_notifications.tasks import parse_received_message_task


class Command(BaseCommand):
    args = ""
    help = "Check if message parsed"

    def handle(self, *args, **options):
        ago = now() - timedelta(minutes=1)
        raws = PhoneReceivedRaw.objects.filter(status=PhoneReceivedRaw.STATUS_PENDING, created__lte=ago)
        for raw in raws:
            parse_received_message_task(raw.id)
