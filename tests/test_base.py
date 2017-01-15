# -*- coding: utf-8 -*-
""" base tests:
    - sending
        - receiver list preparation
        - message serialization
        - sending

    - chaining
        - transformations
        - conditions """
import mock
from django.contrib.auth.models import User
from django.db import models
from rest_framework import serializers
from rest_framework.test import APITestCase

from universal_notifications.notifications import (
    EmailNotification, NotificationBase, PushNotification, SMSNotification, WSNotification)


class SampleA(NotificationBase):
    @classmethod
    def get_type(cls):
        return 'Test'

    def prepare_receivers(self):
        return list(map(lambda x: x.strip(), self.receivers))

    def prepare_message(self):
        return self.item['content']

    def send_inner(self, prepared_receivers, prepared_message):
        pass

    def get_notification_history_details(self):
        return 'whatever'


class SampleB(SampleA):
    chaining = (
        {'class': SampleA, 'delay': 0},
        {'class': SampleA, 'delay': 90},
    )

    def send_inner(self, prepared_receivers, prepared_message):
        pass  # overwrite, so calls to this method are not counted


def set_as_read(item, receivers, context):
    item['is_read'] = True
    return item, receivers, context


def only_not_read(item, receivers, context, parent_result):
    return not item['is_read']


class SampleC(SampleA):
    chaining = (
        {'class': SampleA, 'delay': 0, 'condition_func': only_not_read},
        {'class': SampleA, 'delay': 90, 'transform_func': set_as_read, 'condition_func': only_not_read},
    )

    def send_inner(self, prepared_receivers, prepared_message):
        pass  # overwrite, so calls to this method are not counted


class SampleModel(models.Model):
    name = models.CharField(max_length=128)


class SampleSerializer(serializers.ModelSerializer):
    class Meta:
        model = SampleModel
        fields = ('name',)


class SampleD(WSNotification):
    message = 'WebSocket'
    serializer_class = SampleSerializer


class SampleE(SMSNotification):
    message = '{{item.name}}'


class SampleF(EmailNotification):
    email_name = 'name'
    email_subject = 'subject'


class SampleG(PushNotification):
    message = '{{item.name}}'


class SampleReceiver(object):
    def __init__(self, email, phone, first_name='Foo', last_name='Bar'):
        self.email = email
        self.phone = phone
        self.first_name = first_name
        self.last_name = last_name


class BaseTest(APITestCase):
    def setUp(self):
        self.item = {'content': 'whateva', 'is_read': False}
        self.receivers = ['  a  ', 'b ']

        self.object_item = SampleModel('sample')
        self.object_receiver = SampleReceiver('foo@bar.com', '123456789')
        self.unsubscribed_receiver = SampleReceiver('bar@foo.com', '888777666')

        User.objects.create_user(
            username='user', email=self.unsubscribed_receiver.email, password='1234')

    def test_sending(self):
        """ sending
            - test sending

            TODO (Pawel):
                - test receiver list preparation
                - test message serialization """
        with mock.patch('tests.test_base.SampleA.send_inner') as mocked_send_inner:
            mocked_send_inner.return_value = None

            SampleB(self.item, self.receivers, {}).send()
            mocked_send_inner.assert_called_with(['a', 'b'], 'whateva')
            self.assertEqual(mocked_send_inner.call_count, 2)

            mocked_send_inner.reset_mock()

            SampleC(self.item, self.receivers, {}).send()
            mocked_send_inner.assert_called_with(['a', 'b'], 'whateva')
            self.assertEqual(mocked_send_inner.call_count, 1)

        # test WSNotifications
        with mock.patch('tests.test_base.SampleD.send_inner') as mocked_send_inner:
            SampleD(self.object_item, [self.object_receiver], {}).send()
            mocked_send_inner.assert_called_with({self.object_receiver}, {
                'message': SampleD.message,
                'data': {
                    'name': self.object_item.name
                }
            })

        # test SMSNotifications
        with mock.patch('tests.test_base.SampleE.send_inner') as mocked_send_inner:
            SampleE(self.object_item, [self.object_receiver], {}).send()
            mocked_send_inner.assert_called_with({self.object_receiver.phone}, self.object_item.name)

        # test EmailNotifications
        with mock.patch('tests.test_base.SampleF.send_inner') as mocked_send_inner:
            # test using UnsubscribedModel
            with mock.patch('universal_notifications.notifications.UnsubscribedModel', User):
                SampleF(self.object_item, [self.object_receiver, self.unsubscribed_receiver], {}).send()
                mocked_send_inner.assert_called_with({self.object_receiver}, {
                    'item': self.object_item,
                })

            mocked_send_inner.reset_mock()

            SampleF(self.object_item, [self.object_receiver, self.unsubscribed_receiver], {}).send()
            mocked_send_inner.assert_called_with({self.object_receiver, self.unsubscribed_receiver}, {
                'item': self.object_item,
            })

        with mock.patch('universal_notifications.notifications.send_email') as mocked_send_inner:
            SampleF(self.object_item, [self.object_receiver], {}).send()
            mocked_send_inner.assert_called_with(
                SampleF.email_name, '{first_name} {last_name} <{email}>'.format(**self.object_receiver.__dict__),
                self.object_item.name, {
                    'item': self.object_item,
                    'receiver': self.object_receiver
                })

        # test PushNotifications
        with mock.patch('tests.test_base.SampleG.send_inner') as mocked_send_inner:
            SampleG(self.object_item, [self.object_receiver], {}).send()
            mocked_send_inner.assert_called_with({self.object_receiver}, {
                'message': self.object_item.name,
                'data': {}
            })

    def test_chaining(self):
        pass
