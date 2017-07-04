import os

import mock
import six
from django.contrib.auth.models import User
from django.core.exceptions import ImproperlyConfigured
from django.test.utils import override_settings
from push_notifications.settings import PUSH_NOTIFICATIONS_SETTINGS
from rest_framework.renderers import JSONRenderer
from rest_framework.test import APITestCase
from universal_notifications.backends.push.apns import APNSDataOverflow, apns_send_message
from universal_notifications.backends.push.fcm import fcm_send_message
from universal_notifications.backends.push.gcm import gcm_send_message
from universal_notifications.backends.websockets import publish
from universal_notifications.models import Device

try:
    from urllib.parse import urlencode
except ImportError:
    # Python 2 support
    from urllib import urlencode


class SampleUser(object):
    def __init__(self, email):
        self.email = email


class SampleItem(object):
    def __init__(self, foo="foo"):
        self.foo = foo

    def as_dict(self):
        return {
            "foo": self.foo
        }


class WSTests(APITestCase):
    def setUp(self):
        self.user = SampleUser("user@example.com")
        self.item = SampleItem()

    def test_publish(self):
        with mock.patch("universal_notifications.backends.websockets.RedisMessage") as mocked_message:
            # test without extra arguments
            publish(self.user)
            mocked_message.assert_called_with(JSONRenderer().render({}))

            mocked_message.reset_mock()

            # test with single item
            publish(self.user, self.item)
            mocked_message.assert_called_with(JSONRenderer().render(self.item.as_dict()))

            mocked_message.reset_mock()

            # test with additional_data
            additional_data = {"additional": True}
            publish(self.user, self.item, additional_data)
            result = self.item.as_dict()
            result.update(additional_data)
            mocked_message.assert_called_with(JSONRenderer().render(result))


class PushTests(APITestCase):
    test_settings = {
        "app1": {
            "FCM_API_KEY": "secret",
            "GCM_API_KEY": "secret",
            "APNS_CERTIFICATE": os.path.join(os.path.dirname(__file__), "test_data", "certificate.pem")
        }
    }

    def setUp(self):
        self.user = User.objects.create_user(
            username="user", email="user@example.com", password="1234")

        self.fcm_device = Device(user=self.user, app_id="app1", platform=Device.PLATFORM_FCM)
        self.gcm_device = Device(user=self.user, app_id="app1", platform=Device.PLATFORM_GCM)
        self.apns_device = Device(user=self.user, app_id="app1", platform=Device.PLATFORM_IOS)

    @override_settings(UNIVERSAL_NOTIFICATIONS_MOBILE_APPS=test_settings)
    def test_fcm(self):
        with mock.patch("universal_notifications.backends.push.fcm.FCMNotification."
                        "notify_single_device") as mocked_notify:
            message = {"device": self.fcm_device, "message": "msg", "data": {"stuff": "foo"}}

            with override_settings(UNIVERSAL_NOTIFICATIONS_MOBILE_APPS={"app1": {}}):
                fcm_send_message(**message)
                mocked_notify.assert_not_called()

            mocked_notify.reset_mock()

            fcm_send_message(**message)
            mocked_notify.assert_called_with(registration_id=message["device"].notification_token,
                                             message_body=message["message"], data_message=message["data"])

    @mock.patch("universal_notifications.backends.push.gcm.urlopen")
    def test_gcm(self, mocked_urlopen):
        message = {
            "device": self.fcm_device,
            "message": "msg",
            "collapse_key": "key",
            "delay_while_idle": 1,
            "time_to_live": "1",
            "data": {"info": "foo"}
        }
        with override_settings(UNIVERSAL_NOTIFICATIONS_MOBILE_APPS={"app1": {}}):
            # test sending without API key set
            self.assertRaises(ImproperlyConfigured, gcm_send_message, **message)
            mocked_urlopen.assert_not_called()

        mocked_urlopen.reset_mock()

        with override_settings(UNIVERSAL_NOTIFICATIONS_MOBILE_APPS=self.test_settings):
            # test regular use
            with mock.patch("universal_notifications.backends.push.gcm.Request") as mocked_request:
                mocked_urlopen.return_value.read.return_value = "mocked"
                request_data = {
                    "registration_id": self.gcm_device.notification_token,
                    "collapse_key": message["collapse_key"].encode("utf-8"),
                    "delay_while_idle": message["delay_while_idle"],
                    "time_to_live": message["time_to_live"].encode("utf-8"),
                    "data.message": message["message"].encode("utf-8")
                }
                for k, v in message["data"].items():
                    request_data["data.{}".format(k)] = v.encode("utf-8")

                data = urlencode(sorted(request_data.items())).encode("utf-8")
                self.assertEqual(gcm_send_message(**message), mocked_urlopen.return_value.read.return_value)
                mocked_request.assert_called_with(PUSH_NOTIFICATIONS_SETTINGS["GCM_POST_URL"], data, {
                    "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
                    "Authorization": "key={}".format(self.test_settings["app1"]["GCM_API_KEY"]),
                    "Content-Length": str(len(data)),
                })
                mocked_urlopen.assert_called()

            mocked_urlopen.reset_mock()

            # test fail
            mocked_urlopen.return_value.read.return_value = "Error=Fail"
            self.assertFalse(gcm_send_message(**message))

    def test_apns_config(self):
        message = {
            "device": self.apns_device,
            "message": "msg",
            "data": {}
        }

        # test with no settings
        self.assertRaises(ImproperlyConfigured, apns_send_message, **message)

        # test without certificate set
        with override_settings(UNIVERSAL_NOTIFICATIONS_MOBILE_APPS={"app1": {"GCM_API_KEY": "key"}}):
            self.assertRaises(ImproperlyConfigured, apns_send_message, **message)

        # test unreadable certificate
        with override_settings(UNIVERSAL_NOTIFICATIONS_MOBILE_APPS={"app1": {"APNS_CERTIFICATE": "123d"}}):
            self.assertRaises(ImproperlyConfigured, apns_send_message, **message)

    def test_apns(self):
        message = {
            "device": self.apns_device,
            "message": "msg",
            "data": {}
        }

        with mock.patch("ssl.wrap_socket") as ws:
            with mock.patch("socket.socket") as socket:
                with override_settings(UNIVERSAL_NOTIFICATIONS_MOBILE_APPS=self.test_settings):
                    socket.return_value = 123
                    apns_send_message(**message)
                    ws.assert_called_once_with(
                        123, certfile=self.test_settings["app1"]["APNS_CERTIFICATE"], ssl_version=3)

    @override_settings(UNIVERSAL_NOTIFICATIONS_MOBILE_APPS=test_settings)
    @mock.patch("universal_notifications.backends.push.apns._apns_pack_frame")
    def test_apns_payload(self, mock_pack_frame):
        message = {
            "device": self.apns_device,
            "message": "msg",
            "data": {
                "category": "info",
                "content_available": True,
                "sound": "chime",
                "badge": 1,
                "socket": mock.MagicMock(),
                "identifier": 10,
                "expiration": 30,
                "priority": 20,
                "action_loc_key": "key",
                "loc_key": "TEST_LOCK_KEY",
                "loc_args": "args",
                "extra": {"custom_data": 12345}
            }
        }
        # test rich payload
        apns_send_message(**message)
        mock_pack_frame.assert_called_with(
            self.apns_device.notification_token,
            six.b('{"aps":{"alert":{"action-loc-key":"key","body":"msg","loc-args":"args","loc-key":"TEST_LOCK_KEY"},'
                  '"badge":1,"category":"info","content-available":1,"sound":"chime"},"custom_data":12345}'),
            message["data"]["identifier"], message["data"]["expiration"], message["data"]["priority"]
        )

        # test oversizing
        self.assertRaises(APNSDataOverflow, apns_send_message, self.apns_device, "_" * 2049, {})
