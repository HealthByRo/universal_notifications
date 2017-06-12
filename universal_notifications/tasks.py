# -*- coding: utf-8 -*-
import traceback

import six
from django.conf import settings
from universal_notifications.backends.sms.base import SMS
from universal_notifications.backends.sms.utils import clean_text
from universal_notifications.models import PhonePendingMessages, PhoneReceivedRaw, PhoneReceiver, PhoneSent
from universal_notifications.signals import ws_received

try:
    from django.utils.importlib import import_module
except ImportError:
    from importlib import import_module

__path, __symbol = getattr(settings, "CELERY_APP_PATH").rsplit(".", 1)
app = getattr(import_module(__path), __symbol)


@app.task()
def process_chained_notification(conf, item, receivers, context, parent_result):
    """ conf - configuration of chained notification
        item, receivers, context - parameters for creating Notification subclass
        parent result - result of sending parent notification """

    notification_class = conf["class"]
    transform_func = conf.get("transform_func", None)
    condition_func = conf.get("condition_func", None)

    # parameters transformation
    if transform_func:
        item, receivers, context = transform_func(item, receivers, context)

    # checking if notification should be skipped
    if condition_func:
        if not condition_func(item, receivers, context, parent_result):
            return

    # sending out notification
    notification_class(item, receivers, context).send()


__path, __symbol = getattr(settings, "CELERY_APP_PATH").rsplit(".", 1)
app = getattr(import_module(__path), __symbol)


LOCK_EXPIRE = 60 * 5  # Lock expires in 5 minutes


@app.task(ignore_result=True)
def parse_received_message_task(message_id):
    try:
        raw = PhoneReceivedRaw.objects.get(id=message_id, status=PhoneReceivedRaw.STATUS_PENDING)
    except PhoneReceivedRaw.DoesNotExist:
        return

    try:
        sms = SMS()
        if sms.parse_received(raw):
            raw.status = PhoneReceivedRaw.STATUS_PASS
            raw.save()
    except Exception:
        raw.status = PhoneReceivedRaw.STATUS_FAIL
        raw.exception = traceback.format_exc()
        raw.save()


@app.task(ignore_result=True)
def send_message_task(to_number, text, media, priority):
    sms = SMS()

    try:
        receiver = PhoneReceiver.objects.get(number=to_number)
    except PhoneReceiver.DoesNotExist:
        service_number = sms.get_service_number()
        receiver = PhoneReceiver.objects.create(number=to_number, service_number=service_number)

    obj = PhoneSent()
    obj.receiver = receiver
    obj.text = six.text_type(clean_text(text))
    obj.media_raw = media
    obj.status = PhoneSent.STATUS_QUEUED

    if receiver.is_blocked:
        obj.status = PhoneSent.STATUS_FAILED
        obj.save()
        return

    obj.save()

    data = {
        "from_phone": obj.receiver.service_number,
        "priority": priority,
        "message": obj,
    }
    PhonePendingMessages.objects.create(**data)


@app.task(ignore_result=True)
def ws_received_send_signal_task(message_data, channel_emails):
    ws_received.send(sender=None, message_data=message_data, channel_emails=channel_emails)
