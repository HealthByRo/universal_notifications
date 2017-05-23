from __future__ import absolute_import

from celery import Celery
from django.conf import settings

app = Celery("app.celery")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks(settings.INSTALLED_APPS, related_name="tasks")
