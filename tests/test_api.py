# -*- coding: utf-8 -*-
from rest_framework.reverse import reverse

from tests.test_utils import APIBaseTestCase
from universal_notifications.models import Device


class NotificationApiTestCase(APIBaseTestCase):

    def test_device_api(self):
        self._create_user()
        url = reverse('notifications_devices_api')

        response = self.client.post(url, {})
        self.assertEqual(response.status_code, 401)  # login required - 403 worked

        self._login()
        response = self.client.post(url, {})
        self.assertEqual(response.status_code, 400)
        self.assertIn('platform', response.data)
        self.assertIn('notification_token', response.data)
        self.assertIn('device_id', response.data)
        self.assertIn('app_id', response.data)

        data = {
            'platform': 'wrong',
            'notification_token': 'foo',
            'device_id': 'bar',
            'app_id': 'foo'
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Device.objects.count(), 0)

        data['platform'] = 'ios'
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 201)
        devices = Device.objects.all()
        self.assertEqual(devices.count(), 1)
        self.assertEqual(devices[0].user, self.user)
        self.assertEqual(devices[0].platform, 'ios')
        self.assertEqual(devices[0].notification_token, 'foo')
        self.assertEqual(devices[0].device_id, 'bar')
        self.assertTrue(devices[0].is_active)
