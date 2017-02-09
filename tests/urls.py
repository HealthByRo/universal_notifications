# -*- coding: utf-8 -*-
from django.conf.urls import include, url
from django.contrib import admin

admin.autodiscover()

urlpatterns = [
    url(r'', include('universal_notifications.urls')),
    url(r"^admin/", admin.site.urls),
]
