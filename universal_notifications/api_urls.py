# -*- coding: utf-8 -*-
from django.conf.urls import url
from rest_framework.routers import DefaultRouter
from universal_notifications.api import DevicesAPI, SubscriptionsAPI
from universal_notifications.backends.twilio.api import TwilioAPI

urlpatterns = [
    url(r"^devices$", DevicesAPI.as_view(), name="notifications-devices"),
    url(r"^twilio$", TwilioAPI.as_view(), name="twilio-callback"),
    url(r"^subscriptions$", SubscriptionsAPI.as_view(), name="notifications-subscriptions")
]

router = DefaultRouter()
urlpatterns += router.urls
