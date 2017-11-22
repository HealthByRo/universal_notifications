import re

import phonenumbers
from django.conf import settings
from django.contrib.sites.models import Site
from django.core.mail import mail_admins

try:
    from django.utils.importlib import import_module
except ImportError:
    from importlib import import_module


try:
    from django.urls import reverse
except ImportError:
    # Django < 2.0
    from django.core.urlresolvers import reverse


try:
    __path, __symbol = getattr(settings, 'UNIVERSAL_NOTIFICATIONS_SEND_SMS_FUNC').rsplit('.', 1)
    send_sms = getattr(import_module(__path), __symbol)
except (AttributeError, ImportError):
    def send_sms(to_number, text, media=None, priority=9999, send_async=True):
        """Send SMS/MMS

        Send SMS/MMS

        Arguments:
            to_number {string} -- phone number
            text {string} -- SMS/MMS text

        Keyword Arguments:
            media {string} -- path or url to media file (default: {None})
            priority {number} -- sending order if queued, ascending order (default: {9999})
        """
        from universal_notifications.tasks import send_message_task

        if send_async:
            send_message_task.delay(to_number, text, media, priority)
        else:
            send_message_task(to_number, text, media, priority)

try:
    # Wide UCS-4 build
    emoji_pattern = re.compile(u'['
                               u'\U0001F300-\U0001F64F'
                               u'\U0001F680-\U0001F6FF'
                               u'\u2600-\u26FF\u2700-\u27BF]+',
                               re.UNICODE)
except re.error:
    # Narrow UCS-2 build
    emoji_pattern = re.compile(u'('
                               u'\ud83c[\udf00-\udfff]|'
                               u'\ud83d[\udc00-\ude4f\ude80-\udeff]|'
                               u'[\u2600-\u26FF\u2700-\u27BF])+',
                               re.UNICODE)


def clean_text(text):
    return emoji_pattern.sub(r'', text)


def format_phone(phone):
    if not phone:
        return ''
    region = 'US'
    if phone.startswith('+'):
        region = None
    parsed = phonenumbers.parse(phone, region)
    return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)


def report_admins(subject, raw):
    url = reverse('admin:universal_notifications_phonereceivedraw_change', args=[raw.id])
    domain = Site.objects.get_current().domain
    url = ''.join(['http://', domain])
    mail_admins(subject, 'Message admin: %s' % url)
