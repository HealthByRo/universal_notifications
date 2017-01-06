# -*- coding: utf-8 -*-
from django.conf.urls import url
from rest_framework.routers import DefaultRouter
from universal_notifications.api import DevicesApi

urlpatterns = [
    url(r'^devices$', DevicesApi.as_view(), name='notifications_devices_api'),
]

router = DefaultRouter()
urlpatterns += router.urls
