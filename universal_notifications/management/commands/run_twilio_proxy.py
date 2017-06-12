# -*- coding: utf-8 -*-
import json
import sys
import threading
import traceback
from time import sleep

from django.conf import settings
from django.core.management.base import BaseCommand
from raven.contrib.django import DjangoClient
from redis import StrictRedis
from universal_notifications.models import Phone, PhonePendingMessages
from ws4redis import settings as private_settings


class Queue(threading.Thread):
    def __init__(self, main, phone):
        self.main = main
        self.phone = phone
        threading.Thread.__init__(self)

    def stop(self):
        if self.phone.number in self.main.queues:
            self.main.queues.remove(self.phone.number)

    def check_messages(self):
        count = 1
        while count:
            messages = PhonePendingMessages.objects.filter(from_phone=self.phone.number)
            count = messages.count()
            if count:
                self.process_message(messages[0])
                sleep(60 / self.phone.rate)
        else:
            self.stop()

    def process_message(self, message):
        message.message.send()
        message.message.save()
        message.delete()

    def run(self):
        try:
            self.check_messages()
        except Exception:
            info = sys.exc_info()
            raven_conf = getattr(settings, "RAVEN_CONFIG", False)
            if raven_conf and raven_conf.get("dsn"):
                client = DjangoClient(raven_conf.get("dsn"))
                exc_type, exc_value, exc_traceback = info
                error = str(traceback.format_exception(exc_type, exc_value, exc_traceback))
                client.capture("raven.events.Message", message="Error Sending message",
                               extra={"info": error, "number": self.phone.number})
            raise Exception(info[1], None, info[2])


class Command(BaseCommand):
    args = ""
    help = "Run twilio proxy"
    queues = []

    def create_queue(self, phone):
        if phone.number not in self.queues:
            t = Queue(self, phone)
            t.start()
            self.queues.append(phone.number)

    def handle(self, *args, **options):
        r = StrictRedis(**private_settings.WS4REDIS_CONNECTION)
        p = r.pubsub()
        channel = getattr(settings, "UNIVERSAL_NOTIFICATIONS_TWILIO_DISPATCHER_CHANNEL", "__un_twilio_dispatcher")
        p.subscribe(channel)

        phones = Phone.objects.all()
        for phone in phones:
            self.create_queue(phone)

        while True:
            message = p.get_message()
            if message:
                try:
                    m = json.loads(message["data"])
                    if m.get("number"):
                        try:
                            phone = Phone.objects.get(number=m["number"])
                            self.create_queue(phone)
                        except Phone.DoesNotExist:
                            pass
                except (TypeError, ValueError):
                    pass
            sleep(0.001)  # be nice to the system :)
