from .views import FakeEmailSend
from django.conf.urls import url
from django.contrib.admin.views.decorators import staff_member_required

urlpatterns = [
    url(r"$", staff_member_required(FakeEmailSend.as_view())),
]
