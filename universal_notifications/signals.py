# -*- coding: utf-8 -*-
import django.dispatch

ws_received = django.dispatch.Signal(providing_args=["message_data", "channel_emails"])
