# -*- coding: utf-8 -*-
from django.db import models


class NotificationHistory(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    group = models.CharField(max_length=50)
    klass = models.CharField(max_length=255)
    receiver = models.CharField(max_length=255)
    details = models.TextField()
