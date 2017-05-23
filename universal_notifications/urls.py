# -*- coding: utf-8 -*-
from django.conf.urls import include, url
from rest_framework.routers import DefaultRouter
from universal_notifications.docs import (UniversalNotificationsApiView, UniversalNotificationsResourcesView,
                                          UniversalNotificationsUIView)

urlpatterns = [
    url(r"^$", UniversalNotificationsUIView.as_view(), name="django.swagger.base.view"),
    url(r"^api-docs/$", UniversalNotificationsResourcesView.as_view(), name="django.swagger.resources.view"),
    url(r"^api-docs/(?P<path>.*)/?$", UniversalNotificationsApiView.as_view(), name="django.swagger.api.view"),

    url(r"^emails/", include("universal_notifications.backends.emails.urls")),
    url(r"api/", include("universal_notifications.api_urls")),
]

router = DefaultRouter()
urlpatterns += router.urls
