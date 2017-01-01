# -*- coding: utf-8 -*-
import six
from django.conf import settings
from django.db import models
from universal_notifications.backends.push.apns import apns_send_message
from universal_notifications.backends.push.fcm import fcm_send_message
from universal_notifications.backends.push.gcm import gcm_send_message

AUTH_USER_MODEL = getattr(settings, 'AUTH_USER_MODEL', 'auth.User')


class NotificationHistory(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    group = models.CharField(max_length=50)
    klass = models.CharField(max_length=255)
    receiver = models.CharField(max_length=255)
    details = models.TextField()


class Device(models.Model):
    user = models.ForeignKey(AUTH_USER_MODEL, related_name='devices')
    notification_token = models.TextField()
    device_id = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True, help_text="Inactive devices will not be sent notifications")
    created = models.DateTimeField(auto_now_add=True)
    PLATFORM_IOS = 'ios'
    PLATFORM_GCM = 'gcm'
    PLATFORM_FCM = 'fcm'
    PLATFORM_CHOICES = (
        (PLATFORM_IOS, 'iOS'),
        (PLATFORM_GCM, 'Google Cloud Messagging (deprecated)'),
        (PLATFORM_FCM, 'Firebase Cloud Messaging'),
    )
    app_id = models.CharField(max_length=100)
    platform = models.CharField(max_length=10, choices=PLATFORM_CHOICES)

    def __unicode__(self):
        return "%s (%s)" % (self.user.email or "unknown user", self.device_id)

    def send_message(self, message, **data):
        """Send message to device

        Args:
            message (string): Message string
            **data (dict, optional): Extra data

        Returns:
            boolean: status of sending notification
        """
        if not self.is_active:
            return False

        if not isinstance(message, six.string_types):
            message = unicode(message)
        args = self, message, data

        if self.platform == Device.PLATFORM_GCM:
            return gcm_send_message(*args)
        elif self.platform == Device.PLATFORM_IOS:
            return apns_send_message(*args)
        elif self.platform == Device.PLATFORM_FCM:
            return fcm_send_message(*args)
        else:
            return False
