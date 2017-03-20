# -*- coding: utf-8 -*-
from django.conf import settings
from universal_notifications.tasks import send_message_task

try:
    from django.utils.importlib import import_module
except ImportError:
    from importlib import import_module


try:
    __path, __symbol = getattr(settings, 'UNIVERSAL_NOTIFICATIONS_SEND_SMS_FUNC').rsplit('.', 1)
    send_sms = getattr(import_module(__path), __symbol)
except:
    def send_sms(to_number, text, media=None, priority=9999):
        """Send SMS/MMS

        Send SMS/MMS

        Arguments:
            to_number {string} -- phone number
            text {string} -- SMS/MMS text

        Keyword Arguments:
            media {string} -- path or url to media file (default: {None})
            priority {number} -- sending order if queued, ascending order (default: {9999})
        """
        send_message_task.delay(to_number, text, media, priority)
