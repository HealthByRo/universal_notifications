# -*- coding: utf-8 -*-
from django.conf import settings

try:
    from django.utils.importlib import import_module
except ImportError:
    from importlib import import_module


class SMS(object):

    def __new__(cls):
        __symbol = getattr(settings, 'UNIVERSAL_NOTIFICATIONS_SMS_ENGINE', 'Twilio').lower()
        return getattr(import_module('universal_notifications.backends.sms.engines.' + __symbol), 'Engine')()
