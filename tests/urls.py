# -*- coding: utf-8 -*-
from django.urls import include, re_path
from django.contrib import admin

admin.autodiscover()

urlpatterns = [
    re_path(r"", include("universal_notifications.urls")),
    re_path(r"^admin/", admin.site.urls),
]
