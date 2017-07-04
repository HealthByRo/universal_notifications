# -*- coding: utf-8 -*-
from rest_framework.reverse import reverse
from tests.test_utils import APIBaseTestCase
from universal_notifications.models import Device
from django.utils.translation import ugettext_lazy as _


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
        devices = Device.objects.all()
        self.assertEqual(devices.count(), 1)
        self.assertEqual(devices[0].user, self.user)
        self.assertEqual(devices[0].platform, "ios")
        self.assertEqual(devices[0].notification_token, "foo")
        self.assertEqual(devices[0].device_id, "bar")
        self.assertTrue(devices[0].is_active)

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
