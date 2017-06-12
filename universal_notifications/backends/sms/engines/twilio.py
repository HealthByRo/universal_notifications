from __future__ import absolute_import

import phonenumbers
from django.conf import settings
from redis import StrictRedis
from rest_framework.renderers import JSONRenderer
from twilio.base.exceptions import TwilioException
from twilio.rest import Client
from twilio.rest.lookups import Lookups
from universal_notifications.backends.sms.abstract import SMSEngineAbtract
from universal_notifications.backends.sms.utils import report_admins
from universal_notifications.models import Phone, PhoneReceived, PhoneReceivedRaw, PhoneReceiver, PhoneSent
from ws4redis import settings as private_settings
from ws4redis.redis_store import RedisMessage


def get_twilio_client(lookups=False):
    if lookups:
        return Lookups(settings.UNIVERSAL_NOTIFICATIONS_TWILIO_ACCOUNT,
                       settings.UNIVERSAL_NOTIFICATIONS_TWILIO_TOKEN)
    return Client(settings.UNIVERSAL_NOTIFICATIONS_TWILIO_ACCOUNT,
                  settings.UNIVERSAL_NOTIFICATIONS_TWILIO_TOKEN)


class Engine(SMSEngineAbtract):

    def get_service_number(self):
        phone = Phone.objects.all().order_by('used_count').first()
        if not phone:
            return ''
        phone.used_count += 1
        phone.save()
        return phone.number

    def add_to_queue(self, obj):
        if getattr(settings, 'UNIVERSAL_NOTIFICATIONS_TWILIO_ENABLE_PROXY', False):
            connection = StrictRedis(**private_settings.WS4REDIS_CONNECTION)
            r = JSONRenderer()
            json_data = r.render({'number': obj.from_phone})
            channel = getattr(settings, 'UNIVERSAL_NOTIFICATIONS_TWILIO_DISPATCHER_CHANNEL', '__un_twilio_dispatcher')
            connection.publish(channel, RedisMessage(json_data))
        else:
            self.send(obj.message)
            obj.message.save()

    def send(self, obj):
        if not getattr(settings, 'UNIVERSAL_NOTIFICATIONS_TWILIO_API_ENABLED', False):
            self.status = PhoneSent.STATUS_SENT
            return

        if not obj.sms_id:
            try:
                obj.status = PhoneSent.STATUS_SENT
                if not obj.text:
                    obj.text = '.'  # hack for MMS
                twilio_client = get_twilio_client()
                params = {
                    'body': obj.text,
                    'to': obj.receiver.number,
                    'from_': obj.receiver.service_number,
                }
                if obj.media:
                    if obj.media.startswith(('http://', 'https://')):
                        params['media_url'] = obj.media
                    else:
                        params['media_url'] = "%s%s" % (settings.MEDIA_URL, obj.media_raw)
                message = twilio_client.messages.create(**params)
                obj.sms_id = message.sid
            except TwilioException as e:
                obj.error_message = e
                obj.status = PhoneSent.STATUS_FAILED

    def parse_received(self, raw):
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
                return True

            message.status = raw.data.get('SmsStatus')
            message.error_code = raw.data.get('ErrorCode')
            message.error_message = raw.data.get('ErrorMessage')
            error_codes = getattr(settings, 'UNIVERSAL_NOTIFICATIONS_TWILIO_REPORT_ERRORS',
                                  [30001, 30006, 30007, 30009])
            if message.error_code in error_codes:
                # special report for broken integration/number
                report_admins('Message issue', raw)
            message.save()
        return True

    def validate_mobile(self, value):
        """Validate if number is mobile

        Lookup Twilio info about number and validate if carrier is mobile or voip

        Arguments:
            value {string|phonenumbers.PhoneNumber} -- phone number

        Returns:
            bool -- return True if number is mobile
        """
        if not settings.UNIVERSAL_NOTIFICATIONS_VALIDATE_MOBILE:
            return True

        value = super(Engine, self).validate_mobile(value)
        if not value:
            return False

        number = phonenumbers.format_number(value, phonenumbers.PhoneNumberFormat.E164)
        client = get_twilio_client(lookups=True)
        response = client.phone_numbers.get(number, include_carrier_info=True)
        if response.carrier['type'] not in ['voip', 'mobile']:
            return False
        return True
