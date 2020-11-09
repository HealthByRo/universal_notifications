# -*- coding: utf-8 -*-
"""base tests:

- sending
    - receiver list preparation
    - message serialization
    - sending
"""
import json
from random import randint

import mock
from django.conf import settings
from django.contrib.auth.models import User
from django.core import mail
from django.core.exceptions import ImproperlyConfigured
from django.db import models
from django.test import override_settings
from rest_framework import serializers
from rest_framework.test import APITestCase
from universal_notifications.models import Device, NotificationHistory, UnsubscribedUser
from universal_notifications.notifications import (EmailNotification, PushNotification, SMSNotification,
                                                   WSNotification)


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
    message = "{{receiver.email}}: {{item.name}}"


class SyncSampleE(SampleE):
    send_async = False


class SampleF(EmailNotification):
    email_name = "test"
    email_subject = "subject"
    categories = ["cars", "newsletter"]
    sendgrid_asm = {
        "group_id": 1,
        "groups_to_display": [1, 2]
    }


class SampleG(PushNotification):
    title = "{{item.name}}"
    description = "desc"


class SampleH(EmailNotification):
    email_name = "test"
    email_subject = "subject"
    category = "system"


class SampleI(SampleH):
    category = "default"


class SampleJ(EmailNotification):
    email_name = "test"
    email_subject = "subject"
    check_subscription = False


class SampleNoCategory(EmailNotification):
    email_name = "test"
    email_subject = "subject"
    category = ""


class SampleChatNotification(EmailNotification):
    email_name = "test"
    email_subject = "subject"
    category = "chat"


class SampleNotExistingCategory(EmailNotification):
    email_name = "test"
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

        self.object_item = SampleModel(name="sample")
        self.object_receiver = SampleReceiver("foo@bar.com", "123456789")
        self.object_second_receiver = SampleReceiver("foo@bar.com", "123456789", first_name="foo@bar.com")
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
        sms_message = "{}: {}".format(self.object_receiver.email, self.object_item.name)
        with mock.patch("universal_notifications.notifications.send_sms") as mocked_send_sms:
            SampleE(self.object_item, [self.object_receiver], {}).send()
            mocked_send_sms.assert_called_with(self.object_receiver.phone, sms_message, send_async=True)
            mocked_send_inner.reset_mock()

            SyncSampleE(self.object_item, [self.object_receiver], {}).send()
            mocked_send_sms.assert_called_with(self.object_receiver.phone, sms_message, send_async=False)

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

        mail.outbox = []
        SampleF(self.object_item, [self.object_second_receiver], {}).send()
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, "subject")
        self.assertEqual(mail.outbox[0].to, ["{last_name} <{email}>".format(**self.object_second_receiver.__dict__)])
        self.assertEqual(mail.outbox[0].categories, ["cars", "newsletter"])
        self.assertEqual(mail.outbox[0].asm, {
            "group_id": 1,
            "groups_to_display": [1, 2]
        })

        mail.outbox = []
        notification = SampleF(self.object_item, [self.object_receiver], {})
        notification.sender = "Overriden Sender <overriden@sender.com>"
        notification.send()
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].from_email, "Overriden Sender <overriden@sender.com>")

        # test PushNotifications
        with mock.patch("tests.test_base.SampleG.send_inner") as mocked_send_inner:
            SampleG(self.object_item, [self.object_receiver], {}).send()
            expected_message = {
                "title": self.object_item.name,
                "description": SampleG.description,
                "data": {}
            }
            mocked_send_inner.assert_called_with({self.object_receiver}, expected_message)

        # test send_inner
        with mock.patch("tests.test_base.Device.send_message") as mocked_send_message:
            SampleG(self.object_item, [self.regular_user], {"item": self.object_item}).send()
            mocked_send_message.assert_called_with(self.object_item.name, SampleG.description)

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

    def test_email_attachments(self):
        mail.outbox = []
        attachments = [
            ("first.txt", "first file", "text/plain"),
            ("second.txt", "second file", "text/plain")
        ]
        SampleF(self.object_item, [self.object_receiver], {}, attachments=attachments).send()
        self.assertEqual(len(mail.outbox), 1)
        last_mail = mail.outbox[0]
        self.assertEqual(last_mail.attachments, attachments)

    def test_email_categories(self):
        SampleF(self.object_item, [self.object_receiver], {}).send()
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].categories, ["cars", "newsletter"])

    @override_settings()
    def test_mapping(self):
        del settings.UNIVERSAL_NOTIFICATIONS_USER_CATEGORIES_MAPPING
        result = SampleD.get_mapped_user_notifications_types_and_categories(self.regular_user)
        expected_result = {}
        for key in settings.UNIVERSAL_NOTIFICATIONS_CATEGORIES.keys():
            expected_result[key] = settings.UNIVERSAL_NOTIFICATIONS_CATEGORIES[key].keys()
        self.assertDictEqual(result, expected_result)

    def test_history(self):
        print(NotificationHistory.objects.all())
        self.assertEqual(NotificationHistory.objects.count(), 0)
        with mock.patch("universal_notifications.notifications.logger.info") as mocked_logger:
            SampleD(self.object_item, [self.object_receiver], {}).send()
            mocked_logger.assert_called()
            message = mocked_logger.call_args[0][0].replace("'", "\"")
            message_dict = json.loads(message.split("Notification sent: ")[1])
            self.assertEqual(message_dict, {
                'group': 'WebSocket', 'klass': 'SampleD', 'receiver': 'foo@bar.com',
                'details': 'message: WebSocket, serializer: SampleSerializer', 'category': 'default'
            })
        self.assertEqual(NotificationHistory.objects.count(), 1)

    def test_getting_subject_from_html(self):
        # when subject is not provided in notification definition, the subject is taken from <title></title> tags
        notification = SampleF(self.object_item, [self.object_receiver], {})
        notification.email_subject = None
        notification.send()
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, "Email template used in tests")

        # should raise ImproperlyConfigured when the title tags cannot be found
        notification.email_name = "test_empty"
        notification.email_subject = None
        with self.assertRaises(ImproperlyConfigured):
            notification.send()
        self.assertEqual(len(mail.outbox), 1)
