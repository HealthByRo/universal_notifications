# -*- coding: utf-8 -*-
from django.conf import settings

try:
    from django.utils.importlib import import_module
except ImportError:
    from importlib import import_module

try:
    __path, __symbol = getattr(settings, 'SEND_SMS_FUNC').rsplit('.', 1)
    send_sms = getattr(import_module(__path), __symbol)
except:
    def send_sms(to_number, text, media=None, priority=9999):
        raise NotImplementedError
