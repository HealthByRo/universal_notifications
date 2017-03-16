import mock
from django.contrib.auth.models import User
from rest_framework.test import APITestCase

from universal_notifications.models import Device


class DeviceTest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='user', email='user@example.com', password='1234')

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
