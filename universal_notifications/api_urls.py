# -*- coding: utf-8 -*-
from django.conf.urls import url
from rest_framework.routers import DefaultRouter
from universal_notifications.api import DevicesApi
from universal_notifications.backends.twilio.api import TwilioAPI

urlpatterns = [
    url(r'^devices$', DevicesApi.as_view(), name='notifications_devices_api'),
    url(r'^twilio$', TwilioAPI.as_view(), name='twilio_callback_api'),
]

router = DefaultRouter()
urlpatterns += router.urls
