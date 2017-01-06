# -*- coding: utf-8 -*-
from rest_framework import serializers
from universal_notifications.models import Device


class DeviceSerializer(serializers.ModelSerializer):

    def create(self, data):
        data['user'] = self.context['request'].user
        return super(DeviceSerializer, self).create(data)

    class Meta:
        model = Device
        fields = ['platform', 'notification_token', 'device_id', 'app_id']
