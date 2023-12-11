# -*- coding: utf-8 -*-
from django.urls import include, re_path
from rest_framework.routers import DefaultRouter

urlpatterns = [
    re_path(r"^emails/", include("universal_notifications.backends.emails.urls")),
    re_path(r"api/", include("universal_notifications.api_urls")),
]

router = DefaultRouter()
urlpatterns += router.urls
