# -*- coding: utf-8 -*-
from universal_notifications.docs import (UniversalNotificationsApiView,
                                          UniversalNotificationsResourcesView,
                                          UniversalNotificationsUIView)

from django.conf.urls import url

urlpatterns = [
    url(r'^$', UniversalNotificationsUIView.as_view(), name="django.swagger.base.view"),
    url(r'^api-docs/$', UniversalNotificationsResourcesView.as_view(), name="django.swagger.resources.view"),
    url(r'^api-docs/(?P<path>.*)/?$', UniversalNotificationsApiView.as_view(), name='django.swagger.api.view'),
]
