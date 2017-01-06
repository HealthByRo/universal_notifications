# -*- coding: utf-8 -*-
from rest_framework.generics import CreateAPIView
from universal_notifications.serializers import DeviceSerializer


class DevicesApi(CreateAPIView):
    serializer_class = DeviceSerializer
