# -*- coding: utf-8 -*-
""" base tests:
    - sending
        - receiver list preparation
        - message serialization
        - sending

    - chaining
        - transformations
        - conditions
"""
from random import randint

import mock
from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ImproperlyConfigured
from django.db import models
from django.test import override_settings
from rest_framework import serializers
from rest_framework.test import APITestCase
from universal_notifications.models import Device, UnsubscribedUser
from universal_notifications.notifications import (EmailNotification, NotificationBase, PushNotification,
                                                   SMSNotification, WSNotification)


class SampleA(NotificationBase):
    check_subscription = False
    category = "system"

    @classmethod
    def get_type(cls):
        return "Test"

    def prepare_receivers(self):
        return list(map(lambda x: x.strip(), self.receivers))

    def prepare_message(self):
        return self.item["content"]

    def send_inner(self, prepared_receivers, prepared_message):
        pass

    def get_notification_history_details(self):
        return "whatever"


class SampleB(SampleA):
    chaining = (
        {"class": SampleA, "delay": 0},
        {"class": SampleA, "delay": 90},
    )

    def send_inner(self, prepared_receivers, prepared_message):
        pass  # overwrite, so calls to this method are not counted


def set_as_read(item, receivers, context):
    item["is_read"] = True
    return item, receivers, context


def only_not_read(item, receivers, context, parent_result):
    return not item["is_read"]


class SampleC(SampleA):
    chaining = (
        {"class": SampleA, "delay": 0, "condition_func": only_not_read},
        {"class": SampleA, "delay": 90, "transform_func": set_as_read, "condition_func": only_not_read},
    )

    def send_inner(self, prepared_receivers, prepared_message):
        pass  # overwrite, so calls to this method are not counted


class SampleModel(models.Model):
    name = models.CharField(max_length=128)


class SampleSerializer(serializers.ModelSerializer):
    class Meta:
        model = SampleModel
        fields = ("name",)


class SampleD(WSNotification):
    message = "WebSocket"
    serializer_class = SampleSerializer


class SampleE(SMSNotification):
    message = "{{item.name}}"


class SyncSampleE(SampleE):
    send_async = False


class SampleF(EmailNotification):
    email_name = "name"
    email_subject = "subject"


class SampleG(PushNotification):
    message = "{{item.name}}"


class SampleH(EmailNotification):
    email_name = "name"
    email_subject = "subject"
    category = "system"


class SampleI(SampleH):
    category = "default"


class SampleJ(EmailNotification):
    email_name = "name"
    email_subject = "subject"
    check_subscription = False


class SampleNoCategory(EmailNotification):
    email_name = "name"
    email_subject = "subject"
    category = ""


class SampleChatNotification(EmailNotification):
    email_name = "name"
    email_subject = "subject"
    category = "chat"


class SampleNotExistingCategory(EmailNotification):
    email_name = "name"
    email_subject = "subject"
    category = "some_weird_one"


class SampleReceiver(object):
    def __init__(self, email, phone, first_name="Foo", last_name="Bar", is_superuser=False):
        self.id = 100000 + randint(1, 100)
        self.email = email
        self.phone = phone
        self.first_name = first_name
        self.last_name = last_name
        self.is_superuser = is_superuser


class BaseTest(APITestCase):
    def setUp(self):
        self.item = {"content": "whateva", "is_read": False}
        self.receivers = ["  a  ", "b "]

        self.object_item = SampleModel("sample")
        self.object_receiver = SampleReceiver("foo@bar.com", "123456789")
        self.superuser_object_receiver = SampleReceiver("super_foo@bar.com", "123456789", is_superuser=True)

        self.regular_user = User.objects.create_user(
            username="barszcz",
            email="bar@sz.cz",
            password="1234"
        )
        self.all_unsubscribed_receiver = User.objects.create_user(
            username="all_unsubscribed_user",
            email="bar@foo.com",
            password="1234")

        self.all_unsubscribed_user = UnsubscribedUser.objects.create(
            user=self.all_unsubscribed_receiver,
            unsubscribed_from_all=True
        )

        self.unsubscribed_receiver = User.objects.create_user(
            username="user",
            email="joe@foo.com",
            password="1234")

        self.unsubscribed_user = UnsubscribedUser.objects.create(
            user=self.unsubscribed_receiver,
            unsubscribed={"email": ["default"]}
        )

        self.push_device = Device.objects.create(
            user=self.regular_user, platform=Device.PLATFORM_FCM)

    def test_sending(self):
        with mock.patch("tests.test_base.SampleA.send_inner") as mocked_send_inner:
            mocked_send_inner.return_value = None

            SampleB(self.item, self.receivers, {}).send()
            mocked_send_inner.assert_called_with(["a", "b"], "whateva")
            self.assertEqual(mocked_send_inner.call_count, 2)

            mocked_send_inner.reset_mock()

            SampleC(self.item, self.receivers, {}).send()
            mocked_send_inner.assert_called_with(["a", "b"], "whateva")
            self.assertEqual(mocked_send_inner.call_count, 1)

        # test WSNotifications
        with mock.patch("tests.test_base.SampleD.send_inner") as mocked_send_inner:
            SampleD(self.object_item, [self.object_receiver], {}).send()
            expected_message = {
                "message": SampleD.message,
                "data": {
                    "name": self.object_item.name
                }
            }
            mocked_send_inner.assert_called_with({self.object_receiver}, expected_message)

        # test send_inner
        with mock.patch("universal_notifications.notifications.publish") as mocked_publish:
            SampleD(self.object_item, [self.object_receiver], {}).send()
            mocked_publish.assert_called_with(self.object_receiver, additional_data=expected_message)

        # test SMSNotifications
        with mock.patch("tests.test_base.SampleE.send_inner") as mocked_send_inner:
            SampleE(self.object_item, [self.object_receiver], {}).send()
            mocked_send_inner.assert_called_with({self.object_receiver.phone}, self.object_item.name)

        # test send_inner
        with mock.patch("universal_notifications.notifications.send_sms") as mocked_send_sms:
            SampleE(self.object_item, [self.object_receiver], {}).send()
            mocked_send_sms.assert_called_with(self.object_receiver.phone, self.object_item.name, True)

        with mock.patch("universal_notifications.notifications.send_sms") as mocked_send_sms:
            SyncSampleE(self.object_item, [self.object_receiver], {}).send()
            mocked_send_sms.assert_called_with(self.object_receiver.phone, self.object_item.name, False)

        # test EmailNotifications
        with mock.patch("tests.test_base.SampleF.send_inner") as mocked_send_inner:
            SampleF(self.object_item, [self.object_receiver, self.all_unsubscribed_receiver], {"param": "val"}).send()
            mocked_send_inner.assert_called_with({self.object_receiver}, {
                "item": self.object_item,
                "param": "val"
            })

        # test System EmailNotifications
        with mock.patch("tests.test_base.SampleH.send_inner") as mocked_send_inner:
            SampleH(self.object_item, [self.object_receiver, self.all_unsubscribed_receiver], {}).send()
            mocked_send_inner.assert_called_with({self.object_receiver, self.all_unsubscribed_receiver}, {
                "item": self.object_item,
            })

        # test EmailNotifications with default disabled
        with mock.patch("tests.test_base.SampleI.send_inner") as mocked_send_inner:
            SampleI(self.object_item, [self.object_receiver, self.unsubscribed_receiver], {}).send()
            mocked_send_inner.assert_called_with({self.object_receiver}, {
                "item": self.object_item,
            })

        # test w/o test subscription
        with mock.patch("tests.test_base.SampleJ.send_inner") as mocked_send_inner:
            SampleJ(self.object_item, [self.object_receiver, self.all_unsubscribed_receiver], {}).send()
            mocked_send_inner.assert_called_with({self.object_receiver, self.all_unsubscribed_receiver}, {
                "item": self.object_item,
            })

        with mock.patch("universal_notifications.notifications.send_email") as mocked_send_email:
            SampleF(self.object_item, [self.object_receiver], {}).send()
            mocked_send_email.assert_called_with(
                SampleF.email_name, "{first_name} {last_name} <{email}>".format(**self.object_receiver.__dict__),
                "subject", {
                    "item": self.object_item,
                    "receiver": self.object_receiver
                }, sender=None)

        with mock.patch("universal_notifications.notifications.send_email") as mocked_send_email:
            notification = SampleF(self.object_item, [self.object_receiver], {})
            notification.sender = "Overriden Sender <overriden@sender.com>"
            notification.send()
            mocked_send_email.assert_called_with(
                SampleF.email_name, "{first_name} {last_name} <{email}>".format(**self.object_receiver.__dict__),
                "subject", {
                    "item": self.object_item,
                    "receiver": self.object_receiver
                }, sender="Overriden Sender <overriden@sender.com>")

        # test PushNotifications
        with mock.patch("tests.test_base.SampleG.send_inner") as mocked_send_inner:
            SampleG(self.object_item, [self.object_receiver], {}).send()
            expected_message = {
                "message": self.object_item.name,
                "data": {}
            }
            mocked_send_inner.assert_called_with({self.object_receiver}, expected_message)

        # test send_inner
        with mock.patch("tests.test_base.Device.send_message") as mocked_send_message:
            SampleG(self.object_item, [self.regular_user], {"item": self.object_item}).send()
            mocked_send_message.assert_called_with(self.object_item.name)

        # test w/o category - should fail
        with mock.patch("tests.test_base.SampleNoCategory.send_inner") as mocked_send_inner:
            with self.assertRaises(ImproperlyConfigured):
                SampleNoCategory(self.object_item, [self.object_receiver, self.unsubscribed_receiver], {}).send()

        # chat category is not allowed for "user"
        with self.assertRaises(ImproperlyConfigured):
            SampleChatNotification(self.object_item, [self.object_receiver], {}).send()

        # but works for super user
        with mock.patch("tests.test_base.SampleChatNotification.send_inner") as mocked_send_inner:
            SampleChatNotification(self.object_item, [self.superuser_object_receiver], {}).send()
            mocked_send_inner.assert_called_with({self.superuser_object_receiver}, {
                "item": self.object_item,
            })

        with mock.patch("tests.test_base.SampleNotExistingCategory.send_inner") as mocked_send_inner:
            with self.assertRaises(ImproperlyConfigured):
                SampleNotExistingCategory(self.object_item, [self.object_receiver], {}).send()

    @override_settings()
    def test_mapping(self):
        del settings.UNIVERSAL_NOTIFICATIONS_USER_CATEGORIES_MAPPING
        result = SampleD.get_mapped_user_notifications_types_and_categories(self.regular_user)
        expected_result = {}
        for key in settings.UNIVERSAL_NOTIFICATIONS_CATEGORIES.keys():
            expected_result[key] = settings.UNIVERSAL_NOTIFICATIONS_CATEGORIES[key].keys()
        self.assertDictEqual(result, expected_result)

    def test_chaining(self):
        pass
