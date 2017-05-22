import mock

from universal_notifications.models import Device, PhoneReceiver, PhoneSent
from .test_utils import APIBaseTestCase


class DeviceTest(APIBaseTestCase):
    def setUp(self):
        self.user = self._create_user()

        self.fcm_device = Device(user=self.user, app_id='app1', platform=Device.PLATFORM_FCM)
        self.gcm_device = Device(user=self.user, app_id='app1', platform=Device.PLATFORM_GCM)
        self.apns_device = Device(user=self.user, app_id='app1', platform=Device.PLATFORM_IOS)
        self.inactive_device = Device(user=self.user, app_id='app1', platform=Device.PLATFORM_FCM, is_active=False)
        self.unknown_device = Device(user=self.user, app_id='app1', platform='UNKNOWN')

    def test_send_message(self):
        message = {'message': 'msg', 'field': 'f1'}

        # test using inactive device
        self.assertFalse(self.inactive_device.send_message(**message))

        # test using unknown device platform
        self.assertFalse(self.unknown_device.send_message(**message))

        # test passing non-string message
        with mock.patch('universal_notifications.models.fcm_send_message') as mocked_send_message:
            self.fcm_device.send_message(message=1234, field='1')
            mocked_send_message.assert_called_with(self.fcm_device, '1234', {'field': '1'})
            mocked_send_message.reset_mock()

            # test using fcm device
            self.fcm_device.send_message(**message)
            mocked_send_message.assert_called_with(self.fcm_device, message['message'],
                                                   {'field': message['field']})

        # test using gcm device
        with mock.patch('universal_notifications.models.gcm_send_message') as mocked_send_message:
            self.gcm_device.send_message(**message)
            mocked_send_message.assert_called_with(self.gcm_device, message['message'],
                                                   {'field': message['field']})

        # test using apns device
        with mock.patch('universal_notifications.models.apns_send_message') as mocked_send_message:
            self.apns_device.send_message(**message)
            mocked_send_message.assert_called_with(self.apns_device, message['message'],
                                                   {'field': message['field']})


class PhoneSentTest(APIBaseTestCase):
    def setUp(self):
        self.receiver = PhoneReceiver.objects.create(number='+18023390056', service_number='+18023390056')

    def test_send(self):
        with mock.patch('universal_notifications.backends.sms.base.SMS') as mocked_sms:
            # test sending a message with status different than PENDING or QUEUED
            message = PhoneSent.objects.create(receiver=self.receiver, text='123', status=PhoneSent.STATUS_FAILED)
            message.send()
            mocked_sms.assert_not_called()

            mocked_sms.reset_mock()

            # test sending a queued message
            message = PhoneSent.objects.create(receiver=self.receiver, text='123', status=PhoneSent.STATUS_QUEUED)
            message.send()
            mocked_sms.return_value.send.assert_called_with(message)


class PhoneReceiverTest(APIBaseTestCase):
    def setUp(self):
        self.receiver = PhoneReceiver.objects.create(number='+18023390056', service_number='+18023390056')

    def test_filter(self):
        # test filtering with an incorrect number
        with self.assertRaises(PhoneReceiver.DoesNotExist):
            PhoneReceiver.objects.filter(number='random')

        # test filter
        qs = PhoneReceiver.objects.filter(number=self.receiver.number)
        self.assertEqual(qs.count(), 1)
        self.assertEqual(qs.first().pk, self.receiver.pk)
