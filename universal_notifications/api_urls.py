# -*- coding: utf-8 -*-
from django.urls import re_path
from rest_framework.routers import DefaultRouter

from universal_notifications.api import DeviceDetailsAPI, DevicesAPI, SubscriptionsAPI, UniversalNotificationsDocsView
from universal_notifications.backends.twilio.api import TwilioAPI

urlpatterns = [
    re_path(r"^devices$", DevicesAPI.as_view(), name="notifications-devices"),
    re_path(r"^devices/(?P<pk>\d+)$", DeviceDetailsAPI.as_view(), name="device-details"),
    re_path(r"^twilio$", TwilioAPI.as_view(), name="twilio-callback"),
    re_path(r"^subscriptions$", SubscriptionsAPI.as_view(), name="notifications-subscriptions"),
    re_path(r"^api-docs/", UniversalNotificationsDocsView.as_view(), name="notifications-docs"),
]

router = DefaultRouter()
urlpatterns += router.urls
