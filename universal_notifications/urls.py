# -*- coding: utf-8 -*-
from django.conf.urls import include, url
from rest_framework.routers import DefaultRouter

urlpatterns = [
    url(r"^emails/", include("universal_notifications.backends.emails.urls")),
    url(r"api/", include("universal_notifications.api_urls")),
]

router = DefaultRouter()
urlpatterns += router.urls
