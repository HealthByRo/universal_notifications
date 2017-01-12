# -*- coding: utf-8 -*-
from django.conf.urls import include
from django.conf.urls import patterns
from django.conf.urls import url
from django.contrib import admin

# from universal_notifications.docs import NotificationsDocs

admin.autodiscover()
# NotificationsDocs.autodiscover()

urlpatterns = patterns(
    "",
    url(r'', include('universal_notifications.urls')),
    url(r"^admin/", include(admin.site.urls)),

)
