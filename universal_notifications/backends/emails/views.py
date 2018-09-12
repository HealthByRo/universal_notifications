from django.conf import settings
from django.template import TemplateDoesNotExist
from django.views.generic import TemplateView
from universal_notifications.notifications import EmailNotification


def fake_email_notification_factory(template):
    class FakeEmailNotification(EmailNotification):
        email_name = template
        email_subject = "Fake email!"
        check_subscription = False

        def format_receiver(cls, receiver):
            return receiver

        def format_receiver_for_notification_history(self, receiver):
            return receiver

    return FakeEmailNotification


class FakeEmailSend(TemplateView):
    template_name = "emails/fake.html"

    def get_context_data(self, **kwargs):
        context = super(FakeEmailSend, self).get_context_data(**kwargs)
        context["template"] = self.request.GET.get("template")
        context["email"] = getattr(settings, "UNIVERSAL_NOTIFICATIONS_FAKE_EMAIL_TO", None)
        if context["template"] and context["email"]:
            FakeEmailNotification = fake_email_notification_factory(context["template"])
            try:
                FakeEmailNotification(None, [context["email"]], {}).send()
            except TemplateDoesNotExist:
                context["template_does_not_exist"] = True
        return context
