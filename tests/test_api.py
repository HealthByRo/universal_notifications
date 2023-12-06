# -*- coding: utf-8 -*-
from django.utils.translation import gettext_lazy as _
from rest_framework.reverse import reverse
from tests.test_utils import APIBaseTestCase
from universal_notifications.models import Device


class NotificationApiTestCase(APIBaseTestCase):

    def test_device_api(self):
        self._create_user()
        url = reverse("notifications-devices")

        response = self.client.post(url, {})
        self.assertEqual(response.status_code, 401)  # login required - 403 worked

        self._login()
        response = self.client.post(url, {})
        self.assertEqual(response.status_code, 400)
        self.assertIn("platform", response.data)
        self.assertIn("notification_token", response.data)
        self.assertIn("device_id", response.data)
        self.assertIn("app_id", response.data)

        data = {
            "platform": "wrong",
            "notification_token": "foo",
            "device_id": "bar",
            "app_id": "foo"
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Device.objects.count(), 0)

        data["platform"] = "ios"
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 201)
        first_device_id = response.data["id"]
        devices = Device.objects.all()
        self.assertEqual(devices.count(), 1)
        self.assertEqual(devices[0].user, self.user)
        self.assertEqual(devices[0].platform, "ios")
        self.assertEqual(devices[0].notification_token, "foo")
        self.assertEqual(devices[0].device_id, "bar")
        self.assertTrue(devices[0].is_active)

        # make sure that adding the same device will not duplicate devices
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(devices.count(), 1)
        self.assertEqual(response.data["id"], first_device_id)

    def test_notifications_categories_api(self):
        self._create_user()
        url = reverse("notifications-subscriptions")

        # must be authenticated
        response = self.client.get(url)
        self.assertEqual(response.status_code, 401)

        # labels
        labels_dict = {
            "push": {
                "default": _("This is a label for default category you'll send to FE"),
                "chat": _("Category for chat messages"),
                "promotions": _("Promotions")
            },
            "email": {
                "default": _("This is a label for default category you'll send to FE"),
                "newsletter": _("Newsletter")
            },
            "sms": {
                "default": _("This is a label for default category you'll send to FE"),
                "chat": _("Category for chat messages"),
                "newsletter": _("Newsletter")
            }
        }

        # get
        self._login()
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["unsubscribed_from_all"])
        self.assertEqual(response.data["push"], {
            "default": True,
            "chat": True,
            "promotions": True,
            "unsubscribed_from_all": False
        })
        self.assertEqual(response.data["email"], {
            "default": True,
            "newsletter": True,
            "unsubscribed_from_all": False
        })
        self.assertEqual(response.data["sms"], {
            "default": True,
            "chat": True,
            "newsletter": True,
            "unsubscribed_from_all": False
        })
        self.assertEqual(response.data["labels"], labels_dict)

        # patch is disabled
        response = self.client.patch(url, {}, format="json")
        self.assertEqual(response.status_code, 405)

        # put
        data = {
            "push": {"default": False},
            "email": {"unsubscribed_from_all": True},
            "sms": {
                "default": False,
                "chat": True,
                "newsletter": True,
                "unsubscribed_from_all": False
            }
        }
        response = self.client.put(url, data, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["unsubscribed_from_all"])
        self.assertEqual(response.data["push"], {
            "default": False,
            "chat": True,
            "promotions": True,
            "unsubscribed_from_all": False
        })
        self.assertEqual(response.data["email"], {
            "default": True,
            "newsletter": True,
            "unsubscribed_from_all": True
        })
        self.assertEqual(response.data["sms"], {
            "default": False,
            "chat": True,
            "newsletter": True,
            "unsubscribed_from_all": False
        })

        data = {
            "email": {"unsubscribed_from_all": True},
            "sms": {
                "default": False,
                "chat": True,
                "newsletter": True,
                "unsubscribed_from_all": False
            },
            "unsubscribed_from_all": True
        }
        response = self.client.put(url, data, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["unsubscribed_from_all"])
        self.assertEqual(response.data["push"], {
            "default": True,
            "chat": True,
            "promotions": True,
            "unsubscribed_from_all": False
        })
        self.assertEqual(response.data["email"], {
            "default": True,
            "newsletter": True,
            "unsubscribed_from_all": True
        })
        self.assertEqual(response.data["sms"], {
            "default": False,
            "chat": True,
            "newsletter": True,
            "unsubscribed_from_all": False
        })


class DeviceDetailsAPITestCase(APIBaseTestCase):
    def setUp(self):
        self.user = self._create_user(i=34)
        self.second_user = self._create_user(i=2, set_self=False)
        self.first_device = Device.objects.create(user=self.user, platform=Device.PLATFORM_IOS,
                                                  notification_token="abc", device_id="iphone5,2", app_id="com.abc")
        self.second_device = Device.objects.create(user=self.second_user, platform=Device.PLATFORM_IOS,
                                                   notification_token="abc", device_id="iphone5,2", app_id="com.abc")

    def test_api(self):
        # try deleting other user's device
        url = reverse("device-details", args=[self.second_device.id])
        self._login(self.user)
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 404)

        url = reverse("device-details", args=[self.first_device.id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 204)
