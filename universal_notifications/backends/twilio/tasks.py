# -*- coding: utf-8 -*-
import traceback

import six
from django.conf import settings
from django.contrib.sites.models import Site
from django.core.mail import mail_admins
from django.core.urlresolvers import reverse
from universal_notifications.backends.twilio.utils import clean_text
from universal_notifications.models import (Phone, PhonePendingMessages,
                                            PhoneReceived, PhoneReceivedRaw,
                                            PhoneReceiver, PhoneSent)

try:
    from django.utils.importlib import import_module
except ImportError:
    from importlib import import_module


__path, __symbol = getattr(settings, 'CELERY_APP_PATH').rsplit('.', 1)
app = getattr(import_module(__path), __symbol)


LOCK_EXPIRE = 60 * 5  # Lock expires in 5 minutes


def report_admins(subject, raw):
    url = reverse('admin:universal_notifications_phonereceivedraw_change', args=[raw.id])
    domain = Site.objects.get_current().domain
    url = ''.join(['http://', domain])
    mail_admins(subject, 'Message admin: %s' % url)


@app.task(ignore_result=True)
def parse_received_message_task(message_id):
    try:
        raw = PhoneReceivedRaw.objects.get(id=message_id, status=PhoneReceivedRaw.STATUS_PENDING)
    except PhoneReceivedRaw.DoesNotExist:
        return

    try:
        if raw.data.get('AccountSid') != settings.UNIVERSAL_NOTIFICATIONS_TWILIO_ACCOUNT:
            raw.status = PhoneReceivedRaw.STATUS_REJECTED
            raw.save()
            report_admins('Rejected incoming Twilio message', raw)
            return

        if raw.data.get('Direction') == 'inbound':
            # incoming voice call, handle only recording
            if raw.data.get('RecordingUrl'):
                # TODO: handle calls
                # variables = {'data': raw.data}
                # TODO: handle calls
                # for user in Account.objects.filter(is_superuser=True):
                #     send_email('voice_mail', user.email, 'Patient leaved a voice mail', variables)
                pass
        elif raw.data.get('SmsStatus') == 'received':
            receiver, c = PhoneReceiver.objects.get_or_create(number=raw.data.get('From'),
                                                              service_number=raw.data.get('To'))
            if raw.data.get('SmsMessageSid', ''):
                try:
                    PhoneReceived.objects.get(sms_id=raw.data.get('SmsMessageSid', ''))
                    return
                except PhoneReceived.DoesNotExist:
                    pass

            message = PhoneReceived()
            message.receiver = receiver
            message.media = raw.data.get('MediaUrl0', '')
            message.sms_id = raw.data.get('SmsSid', '')
            message.text = raw.data.get('Body', '')
            message.type = 'text'
            message.raw = raw

            stop_words = getattr(settings, 'UNIVERSAL_NOTIFICATIONS_TWILIO_STOP_WORDS',
                                 ('stop', 'unsubscribe', 'cancel', 'quit', 'end'))
            if message.text.lower() in stop_words and not receiver.is_blocked:
                receiver.is_blocked = True
                receiver.save()
                message.is_opt_out = True

            message.save()

            start_words = getattr(settings, 'UNIVERSAL_NOTIFICATIONS_TWILIO_START_WORDS', ('start',))
            if message.text.lower() in start_words and receiver.is_blocked:
                receiver.is_blocked = False
                receiver.save()
        else:
            try:
                message = PhoneSent.objects.get(sms_id=raw.data.get('SmsSid'))
            except PhoneSent.DoesNotExist:
                return

            message.status = raw.data.get('SmsStatus')
            message.twilio_error_code = raw.data.get('ErrorCode')
            message.twilio_error_message = raw.data.get('ErrorMessage')
            error_codes = getattr(settings, 'UNIVERSAL_NOTIFICATIONS_TWILIO_REPORT_ERRORS',
                                  [30001, 30006, 30007, 30009])
            if message.twilio_error_code in error_codes:
                # special report for broken integration/number
                report_admins('Message issue', raw)
            message.save()

        raw.status = PhoneReceivedRaw.STATUS_PASS
        raw.save()
    except Exception:
        raw.status = PhoneReceivedRaw.STATUS_FAIL
        raw.exception = traceback.format_exc()
        raw.save()


@app.task(ignore_result=True)
def send_message_task(to_number, text, media, priority):
    try:
        receiver = PhoneReceiver.objects.get(number=to_number)
    except PhoneReceiver.DoesNotExist:
        phone = Phone.objects.all().order_by('used_count').first()
        if not phone and settings.TESTING:
            return
        receiver = PhoneReceiver.objects.create(number=to_number, service_number=phone.number)
        phone.used_count += 1
        phone.save()

    obj = PhoneSent()
    obj.receiver = receiver
    obj.text = six.text_type(clean_text(text))
    obj.media_raw = media

    if receiver.is_blocked:
        obj.status = PhoneSent.STATUS_FAILED
        obj.save()
        return

    enable_proxy = getattr(settings, 'UNIVERSAL_NOTIFICATIONS_TWILIO_ENABLE_PROXY', False)
    if enable_proxy:
        obj.status = PhoneSent.STATUS_QUEUED
    obj.save()

    if enable_proxy:
        data = {
            'from_phone': receiver.service_number,
            'priority': priority,
            'message': obj,
        }
        PhonePendingMessages.objects.create(**data)
