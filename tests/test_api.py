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

    def test_notifications_categories_api(self):
        pass
        # self.assertEqual(1, 0)
        """
            Create api to store user unsubcriptions
            - /unsubscribed-user
            - allowed method - get/post/put/patch by the owner?
            - get works as get_or_create - if user exists in db in AUTH_USER_MODEL then create
                and return UnsubscribedUser with categories described below and unsubsribed from all = False.
                IMPORTANT: UNSUBSCRIBED MODEL JSON FIELD IS NEVER RETURNED BY API.
            user object should look like:
            - UnsubscribedUserId
            - account_id (authuser)
            - categories
            -- a list of categories for given user type. Expected is json like:
                {'email': [default (with Human readable help text), etc ]}
            - unsubscribed - just JSON value of unsubscribed field


        Examples from pawel:
        CategorySerializer

        [15:25]
        UnsubscribedSerializer:
         to_representation:
           dla kazdej kategorii CategorySerializer().data

        [15:25]
        to_representation:

        [15:26]
        category_name =   BoolField(value=is_unsubscribed, label=category_label)
        Issues - save and init from unsubscribed field.
        """
