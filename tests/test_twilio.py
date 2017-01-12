# -*- coding: utf-8 -*-
import mock
from django.core import mail
from django.core.management import call_command
from django.core.urlresolvers import reverse
from django.test.utils import override_settings
from tests.test_utils import APIBaseTestCase
from universal_notifications.backends.sms import send_sms
from universal_notifications.backends.twilio.utils import validate_mobile
from universal_notifications.models import (Phone, PhonePendingMessages,
                                            PhoneReceived, PhoneReceivedRaw,
                                            PhoneReceiver, PhoneSent)


class TwilioTestsCase(APIBaseTestCase):

    def setUp(self):
        super(TwilioTestsCase, self).setUp()
        self.twilio_callback_url = reverse('twilio_callback_api')

    def create_raw_data(self, text, **kwargs):
        data = {
            'AccountSid': 'fake',
            'ApiVersion': '2010-04-01',
            'Body': text,
            'From': '+18023390056',
            'FromCity': 'WILMINGTON',
            'FromCountry': 'US',
            'FromState': 'VT',
            'FromZip': '05363',
            'SmsMessageSid': '1',
            'SmsSid': '1',
            'SmsStatus': 'received',
            'To': '+18023390057',
            'ToCity': 'GLENCOE',
            'ToCountry': 'US',
            'ToState': 'MN',
            'ToZip': '55336',
        }
        data.update(kwargs)
        return data


@override_settings(UNIVERSAL_NOTIFICATIONS_TWILIO_ENABLE_PROXY=True)
class ProxyTests(TwilioTestsCase):

    def setUp(self):
        super(ProxyTests, self).setUp()
        self.phone = Phone.objects.create(number='+18023390050')

    def test_add_to_proxy(self):
        def new_message(i, priority, from_phone='+18023390050'):
            m = PhonePendingMessages.objects.all().order_by('-id')
            self.assertEqual(m.count(), i)
            self.assertEqual(m[0].from_phone, from_phone)
            self.assertEqual(m[0].priority, priority)
            self.assertEqual(redis_mock.call_count, i)

        with mock.patch('universal_notifications.models.StrictRedis') as redis_mock:
            send_sms('+18023390051', 'foo')
            new_message(1, 9999)

            send_sms('+18023390051', 'foo', priority=1)
            new_message(2, 1)

    def test_check_queue(self):
        with mock.patch('universal_notifications.models.StrictRedis'):
            PhonePendingMessages.objects.create(from_phone="802-339-0057")
            PhonePendingMessages.objects.create(from_phone="802-339-0057")
            PhonePendingMessages.objects.create(from_phone="802-339-0058")

        with mock.patch('universal_notifications.management.commands.check_twilio_proxy.'
                        'StrictRedis.publish') as redis_mock:
            call_command('check_twilio_proxy')
            self.assertEqual(redis_mock.call_count, 2)


class ReceivedTests(TwilioTestsCase):

    def test_verification(self):
        data = self.create_raw_data('foo')
        r = self.client.post(self.twilio_callback_url, data=data)
        self.assertEqual(r.status_code, 202)
        self.assertEqual(PhoneReceived.objects.count(), 1)
        raw = PhoneReceivedRaw.objects.all()
        self.assertEqual(raw.count(), 1)
        self.assertEqual(raw[0].status, PhoneReceivedRaw.STATUS_PASS)
        self.assertEqual(len(mail.outbox), 0)

        # Wrong account id
        PhoneReceived.objects.all().delete()
        PhoneReceivedRaw.objects.all().delete()
        data['AccountSid'] = 'bar'
        r = self.client.post(self.twilio_callback_url, data=data)
        self.assertEqual(r.status_code, 202)
        self.assertEqual(PhoneReceived.objects.count(), 0)
        raw = PhoneReceivedRaw.objects.all()
        self.assertEqual(raw.count(), 1)
        self.assertEqual(raw[0].status, PhoneReceivedRaw.STATUS_REJECTED)
        self.assertEqual(len(mail.outbox), 1)

    def test_call(self):
        # TODO
        pass
        # data = self.create_raw_data('foo', Direction='inbound', CallStatus='ringing')
        # r = self.client.post(self.twilio_callback_url, data=data)
        # self.assertEqual(r.status_code, 200)
        # self.assertTrue('Hello, thanks for calling' in r.content)
        # self.assertEqual(PhoneReceiver.objects.count(), 0)

        # # Recording
        # self._create_user(is_superuser=True)
        # data = self.create_raw_data('foo', Direction='inbound', CallStatus='completed', RecordingUrl="http://foo.com")
        # r = self.client.post(self.twilio_callback_url, data=data)
        # self.assertEqual(r.status_code, 202)
        # self.assertEqual(len(mail.outbox), 1)

    def test_parse(self):
        data = self.create_raw_data(u'yes😄')
        r = self.client.post(self.twilio_callback_url, data=data)
        self.assertEqual(r.status_code, 202)
        self.assertEqual(PhoneReceived.objects.count(), 1)
        self.assertEqual(PhoneReceived.objects.first().text, 'yes')  # Strip emoji - hard to setup with mysql
        self.assertEqual(PhoneReceivedRaw.objects.count(), 1)
        self.assertEqual(PhoneReceivedRaw.objects.first().status, PhoneReceivedRaw.STATUS_PASS)
        self.assertEqual(PhoneReceiver.objects.count(), 1)
        self.assertFalse(PhoneReceiver.objects.first().is_blocked)

        # Do not add the same twice
        r = self.client.post(self.twilio_callback_url, data=data, format='multipart')
        self.assertEqual(r.status_code, 202)
        self.assertEqual(PhoneReceived.objects.count(), 1)
        self.assertEqual(PhoneReceivedRaw.objects.count(), 2)

    def test_special_words(self):
        # stop
        data = self.create_raw_data(u'QuiT')
        r = self.client.post(self.twilio_callback_url, data=data, format='multipart')
        self.assertEqual(r.status_code, 202)
        self.assertEqual(PhoneReceiver.objects.count(), 1)
        self.assertTrue(PhoneReceiver.objects.first().is_blocked)

        # start
        data = self.create_raw_data(u'StarT', SmsMessageSid='2')
        r = self.client.post(self.twilio_callback_url, data=data, format='multipart')
        self.assertEqual(r.status_code, 202)
        self.assertEqual(PhoneReceiver.objects.count(), 1)
        self.assertFalse(PhoneReceiver.objects.first().is_blocked)


class SentTests(TwilioTestsCase):

    def setUp(self):
        super(SentTests, self).setUp()
        self.phone = Phone.objects.create(number='+18023390050')

    @override_settings(UNIVERSAL_NOTIFICATIONS_TWILIO_API_ENABLED=True)
    def test_send(self):
        with mock.patch('universal_notifications.models.get_twilio_client') as call_mock:
            call_mock.return_value.messages.create.return_value.sid = 123
            send_sms('+18023390056', u'foo😄')

            mocked_data = {
                'body': 'foo',
                'to': '+18023390056',
                'from_': '+18023390050',
            }
            self.assertEqual(call_mock.return_value.messages.create.call_args[1], mocked_data)
            r = PhoneReceiver.objects.get(number='+18023390056')
            s = PhoneSent.objects.all()
            self.assertEqual(s.count(), 1)
            self.assertEqual(s[0].receiver, r)
            self.assertEqual(s[0].status, PhoneSent.STATUS_SENT)
            self.assertEqual(s[0].text, 'foo')  # Strip emoji - hard to setup with mysql base settings

    @override_settings(UNIVERSAL_NOTIFICATIONS_TWILIO_API_ENABLED=True)
    def test_send_blocked(self):
        r = PhoneReceiver.objects.create(number='+18023390056', service_number='+18023390056', is_blocked=True)
        with mock.patch('universal_notifications.models.get_twilio_client') as call_mock:
            call_mock.return_value.messages.create.return_value.sid = 123
            send_sms('+18023390056', u'foo😄')

            self.assertEqual(call_mock.call_count, 0)
            s = PhoneSent.objects.all()
            self.assertEqual(s.count(), 1)
            self.assertEqual(s[0].receiver, r)
            self.assertEqual(s[0].status, PhoneSent.STATUS_FAILED)


class UtilsTests(TwilioTestsCase):

    @override_settings(UNIVERSAL_NOTIFICATIONS_VALIDATE_MOBILE=True)
    def test_validate_mobile(self):
        self.assertFalse(validate_mobile('+1'))
        with mock.patch('universal_notifications.backends.twilio.utils.get_twilio_client') as twilio_mock:
            twilio_mock.return_value.phone_numbers.get.return_value.carrier = {'type': 'foo'}
            self.assertFalse(validate_mobile('+18023390050'))
            self.assertEqual(twilio_mock.return_value.phone_numbers.get.call_args[0], ('+18023390050',))
            self.assertEqual(twilio_mock.return_value.phone_numbers.get.call_args[1], {'include_carrier_info': True})

            # twilio_mock.return_value.phone_numbers.get.return_value.carrier.type = 'mobile'
            twilio_mock.return_value.phone_numbers.get.return_value.carrier = {'type': 'mobile'}
            self.assertTrue(validate_mobile('+18023390050'))

            twilio_mock.return_value.phone_numbers.get.return_value.carrier = {'type': 'voip'}
            self.assertTrue(validate_mobile('+18023390050'))
