# -*- coding: utf-8 -*-
import mock
from django.test.utils import override_settings
from tests.test_utils import APIBaseTestCase
from universal_notifications.backends.sms.utils import send_sms
from universal_notifications.models import (PhoneReceiver, PhoneSent)


@override_settings(UNIVERSAL_NOTIFICATIONS_SMS_ENGINE="amazonsns")
class AmazonSNSTestsCase(APIBaseTestCase):

    @override_settings(UNIVERSAL_NOTIFICATIONS_AMAZON_SNS_API_ENABLED=True)
    def test_send(self):
        with mock.patch("universal_notifications.backends.sms.engines.amazonsns.get_sns_client") as call_mock:
            call_mock.return_value.publish.return_value = {"MessageId": "mid"}
            send_sms("+18023390056", u"foo😄")

        mocked_data = {
            "Message": "foo",
            "PhoneNumber": "+18023390056",
        }
        self.assertEqual(call_mock.return_value.publish.call_args[1], mocked_data)
        r = PhoneReceiver.objects.get(number="+18023390056")
        s = PhoneSent.objects.all()
        self.assertEqual(s.count(), 1)
        self.assertEqual(s[0].receiver, r)
        self.assertEqual(s[0].sms_id, "mid")
        self.assertEqual(s[0].status, PhoneSent.STATUS_SENT)
        self.assertEqual(s[0].text, "foo")  # Strip emoji - hard to setup with mysql base settings
