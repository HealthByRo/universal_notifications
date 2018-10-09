# -*- coding: utf-8 -*-
from rest_framework import status
from rest_framework.generics import CreateAPIView, DestroyAPIView, GenericAPIView
from rest_framework.mixins import RetrieveModelMixin, UpdateModelMixin
from rest_framework.permissions import IsAuthenticated
from universal_notifications.models import Device, UnsubscribedUser
from universal_notifications.serializers import DeviceSerializer, UnsubscribedSerializer


class DevicesAPI(CreateAPIView):
    serializer_class = DeviceSerializer

    def create(self, request, *args, **kwargs):
        response = super(DevicesAPI, self).create(request, *args, **kwargs)
        if getattr(self, "_matching_device", None):
            response.status_code = status.HTTP_200_OK

        return response


class DeviceDetailsAPI(DestroyAPIView):
    queryset = Device.objects.all()
    serializer_class = DeviceSerializer

    def get_queryset(self):
        return super(DeviceDetailsAPI, self).get_queryset().filter(user=self.request.user)


class SubscriptionsAPI(RetrieveModelMixin, UpdateModelMixin, GenericAPIView):  # we don't want patch here
    serializer_class = UnsubscribedSerializer
    queryset = UnsubscribedUser.objects.all()
    permission_classes = (IsAuthenticated,)

    def get_object(self):
        obj, created = UnsubscribedUser.objects.get_or_create(user=self.request.user)
        return obj

    def get(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)

    def put(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)
