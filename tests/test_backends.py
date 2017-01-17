import mock
from django.core import mail
from django.contrib.auth.models import User
from django.test.utils import override_settings
from rest_framework.test import APITestCase
from rest_framework.renderers import JSONRenderer

from universal_notifications.backends.emails import send_email
from universal_notifications.backends.websockets import publish
from universal_notifications.backends.push.fcm import fcm_send_message
from universal_notifications.models import Device


class SampleUser(object):
    def __init__(self, email):
        self.email = email


class SampleItem(object):
    def __init__(self, foo='foo'):
        self.foo = foo

    def as_dict(self):
        return {
            'foo': self.foo
        }


class WSTests(APITestCase):
    def setUp(self):
        self.user = SampleUser('user@example.com')
        self.item = SampleItem()

    def test_publish(self):
        with mock.patch('universal_notifications.backends.websockets.RedisMessage') as mocked_message:
            # test without extra arguments
            publish(self.user)
            mocked_message.assert_called_with(JSONRenderer().render({}))

            mocked_message.reset_mock()

            # test with single item
            publish(self.user, self.item)
            mocked_message.assert_called_with(JSONRenderer().render(self.item.as_dict()))

            mocked_message.reset_mock()

            # test with additional_data
            additional_data = {'additional': True}
            publish(self.user, self.item, additional_data)
            result = self.item.as_dict()
            result.update(additional_data)
            mocked_message.assert_called_with(JSONRenderer().render(result))


class EmailTests(APITestCase):
    def test_send_email(self):
        sample_email = {
            'to': 'Foo Bar <foo@bar.com>',
            'subject': 'subject',
            'message': 'template'
        }
        with mock.patch('universal_notifications.backends.emails.render_to_string',
                        lambda x, y: sample_email['message']):
            send_email('email', sample_email['to'], sample_email['subject'], {})
            self.assertEqual(len(mail.outbox), 1)
            sent_email = mail.outbox[0]
            self.assertEqual(sent_email.subject, sample_email['subject'])
            self.assertEqual(sent_email.to, [sample_email['to']])
            self.assertIn(sample_email['message'], sent_email.body)


class PushTests(APITestCase):
    test_settings = {
        'app1': {
            'FCM_API_KEY': 'secret'
        }
    }

    def setUp(self):
        self.user = User.objects.create_user(
            username='user', email='user@example.com', password='1234')

        self.fcm_device = Device(user=self.user, app_id='app1', platform=Device.PLATFORM_FCM)

    @override_settings(UNIVERSAL_NOTIFICATIONS_MOBILE_APPS=test_settings)
    def test_fcm(self):
        with mock.patch('universal_notifications.backends.push.fcm.FCMNotification.'
                        'notify_single_device') as mocked_notify:
            message = {'device': self.fcm_device, 'message': 'msg', 'data': {'stuff': 'foo'}}

            with override_settings(UNIVERSAL_NOTIFICATIONS_MOBILE_APPS={'app1': {}}):
                fcm_send_message(**message)
                mocked_notify.assert_not_called()

            mocked_notify.reset_mock()

            fcm_send_message(**message)
            mocked_notify.assert_called_with(registration_id=message['device'].notification_token,
                                             message_body=message['message'], data_message=message['data'])
