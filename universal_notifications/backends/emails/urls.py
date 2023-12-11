from django.urls import re_path
from django.contrib.admin.views.decorators import staff_member_required

from universal_notifications.backends.emails.views import FakeEmailSend

urlpatterns = [
    re_path(r"$", staff_member_required(FakeEmailSend.as_view()), name="backends.emails.fake_view"),
]
