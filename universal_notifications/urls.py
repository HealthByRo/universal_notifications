# -*- coding: utf-8 -*-
from django.conf.urls import url
from universal_notifications.docs import (UniversalNotificationsApiView,
                                          UniversalNotificationsResourcesView,
                                          UniversalNotificationsUIView)

urlpatterns = [
    url(r'^$', UniversalNotificationsUIView.as_view(), name="django.swagger.base.view"),
    url(r'^api-docs/$', UniversalNotificationsResourcesView.as_view(), name="django.swagger.resources.view"),
    url(r'^api-docs/(?P<path>.*)/?$', UniversalNotificationsApiView.as_view(), name='django.swagger.api.view'),
]
