from django.conf.urls import url
from django.contrib.admin.views.decorators import staff_member_required
from universal_notifications.backends.emails.views import FakeEmailSend

urlpatterns = [
    url(r"$", staff_member_required(FakeEmailSend.as_view()), name="backends.emails.fake_view"),
]
