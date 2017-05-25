# -*- coding: utf-8 -*-
from django.conf import settings
from django.core.management.base import BaseCommand
from redis import StrictRedis
from rest_framework.renderers import JSONRenderer
from universal_notifications.models import PhonePendingMessages
from ws4redis import settings as private_settings
from ws4redis.redis_store import RedisMessage


class Command(BaseCommand):
    args = ""
    help = "Check twilio proxy"

    def handle(self, *args, **options):
        connection = StrictRedis(**private_settings.WS4REDIS_CONNECTION)
        numbers = PhonePendingMessages.objects.all().values_list("from_phone", flat=True).distinct()
        for n in numbers:
            r = JSONRenderer()
            json_data = r.render({"number": n})
            channel = getattr(settings, "UNIVERSAL_NOTIFICATIONS_TWILIO_DISPATCHER_CHANNEL", "__un_twilio_dispatcher")
            connection.publish(channel, RedisMessage(json_data))
