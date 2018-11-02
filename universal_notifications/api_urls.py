# -*- coding: utf-8 -*-
from django.conf.urls import url
from rest_framework.routers import DefaultRouter
from universal_notifications.api import DeviceDetailsAPI, DevicesAPI, SubscriptionsAPI, UniversalNotificationsDocsView
from universal_notifications.backends.twilio.api import TwilioAPI

urlpatterns = [
    url(r"^devices$", DevicesAPI.as_view(), name="notifications-devices"),
    url(r"^devices/(?P<pk>[\d]+)$", DeviceDetailsAPI.as_view(), name="device-details"),
    url(r"^twilio$", TwilioAPI.as_view(), name="twilio-callback"),
    url(r"^subscriptions$", SubscriptionsAPI.as_view(), name="notifications-subscriptions"),
    url(r"^api-docs/", UniversalNotificationsDocsView.as_view(), name="notifications-docs")
]

router = DefaultRouter()
urlpatterns += router.urls
