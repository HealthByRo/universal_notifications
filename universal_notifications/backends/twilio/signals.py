# -*- coding: utf-8 -*-
from django.conf import settings

try:
    from django.utils.importlib import import_module
except ImportError:
    from importlib import import_module

try:
    __path, __symbol = getattr(settings, 'PHONE_RECEIVED_POST_SAVE_FUNC').rsplit('.', 1)
    phone_received_post_save = getattr(import_module(__path), __symbol)
except:
    def phone_received_post_save(sender, instance, created, **kwargs):
        pass
