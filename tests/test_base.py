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
from rest_framework.test import APITestCase

from universal_notifications.notifications import NotificationBase


class SampleA(NotificationBase):
    @classmethod
    def get_type(cls):
        return 'Test'

    def prepare_receivers(self):
        return map(lambda x: x.strip(), self.receivers)

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


class BaseTest(APITestCase):
    def setUp(self):
        self.item = {'content': 'whateva', 'is_read': False}
        self.receivers = ['  a  ', 'b ']

    def test_sending(self):
        """ sending
            - test sending

            TODO (Pawel):
                - test receiver list preparation
                - test message serialization """
        with mock.patch('universal_notifications.tests.test_base.SampleA.send_inner') as mocked_send_inner:
            mocked_send_inner.return_value = None

            SampleB(self.item, self.receivers, {}).send()
            mocked_send_inner.assert_called_with(['a', 'b'], 'whateva')
            self.assertEqual(mocked_send_inner.call_count, 2)

            mocked_send_inner.reset_mock()

            SampleC(self.item, self.receivers, {}).send()
            mocked_send_inner.assert_called_with(['a', 'b'], 'whateva')
            self.assertEqual(mocked_send_inner.call_count, 1)

    def test_chaining(self):
        pass
