# -*- coding: utf-8 -*-
import six
from django.conf import settings
from django.db import models
from django.db.models.signals import post_save
from phonenumbers import NumberParseException
from redis import StrictRedis
from rest_framework.renderers import JSONRenderer
from twilio.rest.exceptions import TwilioRestException
from universal_notifications.backends.push.apns import apns_send_message
from universal_notifications.backends.push.fcm import fcm_send_message
from universal_notifications.backends.push.gcm import gcm_send_message
from universal_notifications.backends.twilio.fields import JSONField
from universal_notifications.backends.twilio.signals import \
    phone_received_post_save
from universal_notifications.backends.twilio.utils import (format_phone,
                                                           get_twilio_client)
from ws4redis import settings as private_settings
from ws4redis.redis_store import RedisMessage

AUTH_USER_MODEL = getattr(settings, 'AUTH_USER_MODEL', 'auth.User')
TWILIO_MAX_RATE = getattr(settings, 'UNIVERSAL_NOTIFICATIONS_TWILIO_MAX_RATE', 6)


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


class Phone(models.Model):
    number = models.CharField(max_length=20, unique=True)
    rate = models.IntegerField('Messages rate', default=TWILIO_MAX_RATE)
    used_count = models.IntegerField(default=0)

    class Meta:
        ordering = ['number']

    def __unicode__(self):
        return self.number

    def save(self, *args, **kwargs):
        self.number = format_phone(self.number)
        return super(Phone, self).save(*args, **kwargs)


class PhoneReceiverManager(models.Manager):

    def format_fields(self, filters):
        for field in ['number', 'service_number']:
            if field in filters:
                try:
                    filters[field] = format_phone(filters[field])
                except NumberParseException:
                    raise PhoneReceiver.DoesNotExist
            return filters

    def filter(self, *args, **filters):
        filters = self.format_fields(filters)
        return super(PhoneReceiverManager, self).filter(*args, **filters)

    def get(self, **filters):
        filters = self.format_fields(filters)
        return super(PhoneReceiverManager, self).get(**filters)


class PhoneReceiver(models.Model):
    number = models.CharField(max_length=20, db_index=True)
    service_number = models.CharField(max_length=20)
    is_blocked = models.BooleanField(default=False)

    objects = PhoneReceiverManager()

    class Meta:
        ordering = ['number']
        index_together = (
            ('number', 'service_number'),
        )

    def __unicode__(self):
        return self.number

    def save(self, *args, **kwargs):
        self.number = format_phone(self.number)
        self.service_number = format_phone(self.service_number)
        return super(PhoneReceiver, self).save(*args, **kwargs)


class PhoneSent(models.Model):
    receiver = models.ForeignKey(PhoneReceiver)
    text = models.TextField()
    sms_id = models.CharField(max_length=34, blank=True)
    STATUS_PENDING = 'pending'
    STATUS_QUEUED = 'queued'
    STATUS_FAILED = 'failed'
    STATUS_SENT = 'sent'
    STATUS_DELIVERED = 'delivered'
    STATUS_UNDELIVERED = 'undelivered'
    STATUS_NO_ANSWER = 'no_answer'
    STATUS_CHOICES = (
        (STATUS_PENDING, 'Pending'),
        (STATUS_QUEUED, 'Queued'),
        (STATUS_FAILED, 'failed'),
        (STATUS_SENT, 'sent'),
        (STATUS_NO_ANSWER, 'no answer from twilio'),
        (STATUS_DELIVERED, 'delivered'),
        (STATUS_UNDELIVERED, 'undelivered'),
    )
    status = models.CharField(max_length=35, choices=STATUS_CHOICES, default='pending')
    twilio_error_code = models.CharField(max_length=100, blank=True, null=True)
    twilio_error_message = models.TextField(blank=True, null=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    media_raw = models.CharField(max_length=255, blank=True, null=True)
    media = models.CharField(max_length=255, blank=True, null=True)

    def send(self):
        if self.status not in [PhoneSent.STATUS_QUEUED, PhoneSent.STATUS_PENDING]:
            return

        if not getattr(settings, 'UNIVERSAL_NOTIFICATIONS_TWILIO_API_ENABLED', False):
            self.status = PhoneSent.STATUS_SENT
            return

        if not self.sms_id:
            try:
                self.status = PhoneSent.STATUS_SENT
                if not self.text:
                    self.text = '.'  # hack for MMS
                twilio_client = get_twilio_client()
                params = {
                    'body': self.text,
                    'to': self.receiver.number,
                    'from_': self.receiver.service_number,
                }
                if self.media:
                    if self.media.startswith(('http://', 'https://')):
                        params['media_url'] = self.media
                    else:
                        params['media_url'] = "%s%s" % (settings.MEDIA_URL, self.media_raw)
                message = twilio_client.messages.create(**params)
                self.sms_id = message.sid
            except TwilioRestException as e:
                self.twilio_error_message = e
                self.status = PhoneSent.STATUS_FAILED

    def save(self, **kwargs):
        if self.status == PhoneSent.STATUS_PENDING:
            self.send()
        return super(PhoneSent, self).save(**kwargs)

    class Meta:
        verbose_name = 'Sent Message'
        verbose_name_plural = verbose_name + 's'


class PhoneReceivedRaw(models.Model):
    STATUS_PENDING = 'pending'
    STATUS_PASS = 'pass'
    STATUS_FAIL = 'fail'
    STATUS_REJECTED = 'rejected'
    STATUS_CHOICES = (
        (STATUS_PENDING, 'Pending'),
        (STATUS_PASS, 'Pass'),
        (STATUS_FAIL, 'Fail'),
        (STATUS_REJECTED, 'Rejected'),
    )
    status = models.CharField(max_length=35, choices=STATUS_CHOICES, default=STATUS_PENDING, db_index=True)
    data = JSONField()
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    exception = models.TextField(blank=True)

    def save(self, *args, **kwargs):
        from universal_notifications.backends.twilio.tasks import parse_received_message_task

        super(PhoneReceivedRaw, self).save(*args, **kwargs)
        if self.status == PhoneReceivedRaw.STATUS_PENDING:
            parse_received_message_task.delay(self.id)


class PhoneReceived(models.Model):
    TYPE_TEXT = 'text'
    TYPE_VOICE = 'voice'
    Type_choices = (
        (TYPE_VOICE, 'voice'),
        (TYPE_TEXT, 'Text'),
    )
    receiver = models.ForeignKey(PhoneReceiver)
    text = models.TextField()
    media = models.CharField(max_length=255, blank=True, null=True)
    sms_id = models.CharField(max_length=34)
    type = models.CharField(max_length=35, choices=Type_choices, default=TYPE_TEXT)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    sms_id = models.CharField(blank=True, max_length=50)
    raw = models.ForeignKey(PhoneReceivedRaw, null=True, blank=True, editable=False, on_delete=models.SET_NULL)
    is_opt_out = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'Received Message'
        verbose_name_plural = verbose_name + 's'


post_save.connect(phone_received_post_save, sender=PhoneReceived)


class PhonePendingMessages(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    from_phone = models.CharField(max_length=30, db_index=True)
    priority = models.IntegerField(default=9999)
    message = models.ForeignKey(PhoneSent, blank=True, null=True)

    def save(self, *args, **kwargs):
        created = not self.id
        self.from_phone = format_phone(self.from_phone)
        ret = super(PhonePendingMessages, self).save(*args, **kwargs)
        if created:
            connection = StrictRedis(**private_settings.WS4REDIS_CONNECTION)
            r = JSONRenderer()
            json_data = r.render({'number': self.from_phone})
            channel = getattr(settings, 'UNIVERSAL_NOTIFICATIONS_TWILIO_DISPATCHER_CHANNEL', '__un_twilio_dispatcher')
            connection.publish(channel, RedisMessage(json_data))

        return ret
