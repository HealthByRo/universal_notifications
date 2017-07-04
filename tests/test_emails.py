import mock
from django.conf import settings
from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase
from universal_notifications.backends.emails.send import send_email

try:
    from django.urls import reverse_lazy
except ImportError:
    # Django < 2.0
    from django.core.urlresolvers import reverse_lazy  # noqa: F401


class EmailTests(TestCase):
    def setUp(self):
        User.objects.create_superuser(
            username="admin",
            email="ad@m.in",
            password="1234"
        )

    def test_send_email(self):
        sample_email = {
            "to": "Foo Bar <foo@bar.com>",
            "subject": "subject",
            "message": "email {A}-{B}",
            "replace_variables": {"A": None, "B": "foo"}
        }
        with mock.patch("universal_notifications.backends.emails.send.render_to_string",
                        lambda x, y: sample_email["message"]):
            send_email("email", sample_email["to"], sample_email["subject"], {},
                       replace_variables=sample_email["replace_variables"])
            self.assertEqual(len(mail.outbox), 1)
            sent_email = mail.outbox[0]
            self.assertEqual(sent_email.subject, sample_email["subject"])
            self.assertEqual(sent_email.to, [sample_email["to"]])
            self.assertIn("email -foo", sent_email.body)

    def test_fake_email_view(self):
        self.client.login(username="admin", password="1234")
        data = {
            "template": "password_recovery",
            "email": settings.UNIVERSAL_NOTIFICATIONS_FAKE_EMAIL_TO,
            "message": "Fake email!"
        }
        with mock.patch("universal_notifications.backends.emails.views.send_email") as mocked_send_email:
            response = self.client.get("{}?template={}".format(
                reverse_lazy("backends.emails.fake_view"), data["template"]))
            self.assertEqual(response.status_code, 200)
            mocked_send_email.assert_called_with(data["template"], data["email"], data["message"])

        # test catching non existing templates
        response = self.client.get("{}?template={}".format(
            reverse_lazy("backends.emails.fake_view"), data["template"]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["template_does_not_exist"], True)
