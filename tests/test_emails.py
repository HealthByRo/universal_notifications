from django.conf import settings
from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase
from django.urls import reverse_lazy


class EmailTests(TestCase):
    def setUp(self):
        User.objects.create_superuser(
            username="admin",
            email="ad@m.in",
            password="1234"
        )

    def test_fake_email_view(self):
        self.client.login(username="admin", password="1234")
        data = {
            "template": "test",
            "email": settings.UNIVERSAL_NOTIFICATIONS_FAKE_EMAIL_TO
        }
        response = self.client.get("{}?template={}".format(
            reverse_lazy("backends.emails.fake_view"), data["template"]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [data["email"]])
        self.assertIn("Email template used in tests", mail.outbox[0].body)

        # test catching non existing templates
        data["template"] = "randomtemplate"
        response = self.client.get("{}?template={}".format(
            reverse_lazy("backends.emails.fake_view"), data["template"]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["template_does_not_exist"], True)
