# -*- coding: utf-8 -*-
from django.test.utils import override_settings
from tests.test_utils import APIBaseTestCase
from universal_notifications.backends.sms.abstract import SMSEngineAbtract
from universal_notifications.models import PhoneReceivedRaw, PhoneSent, PhonePendingMessages


class SNSTestsCase(APIBaseTestCase):

    def setUp(self):
        self.engine = SMSEngineAbtract()

    def test_get_service_number(self):
        self.assertEqual(self.engine.get_service_number(), "")

    def test_add_to_queue(self):
        with self.assertRaises(NotImplementedError):
            obj = PhonePendingMessages()
            self.engine.add_to_queue(obj)

    def test_send(self):
        with self.assertRaises(NotImplementedError):
            obj = PhoneSent()
            self.engine.send(obj)

    def test_parse_received(self):
        with self.assertRaises(NotImplementedError):
            obj = PhoneReceivedRaw()
            self.engine.parse_received(obj)

    def test_validate_mobile(self):
        # disabled so allow all
        with override_settings(UNIVERSAL_NOTIFICATIONS_VALIDATE_MOBILE=False):
            self.assertTrue(self.engine.validate_mobile("fooo"))

        with override_settings(UNIVERSAL_NOTIFICATIONS_VALIDATE_MOBILE=True):
            self.assertFalse(self.engine.validate_mobile("+1"))
            self.assertTrue(self.engine.validate_mobile("+18023390050"))
