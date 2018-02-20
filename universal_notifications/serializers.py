# -*- coding: utf-8 -*-
from django.conf import settings
from rest_framework import serializers
from universal_notifications.models import Device
from universal_notifications.notifications import NotificationBase


class DeviceSerializer(serializers.ModelSerializer):

    def create(self, data):
        data["user"] = self.context["request"].user
        return super(DeviceSerializer, self).create(data)

    class Meta:
        model = Device
        fields = ["platform", "notification_token", "device_id", "app_id"]


class UnsubscribedSerializer(serializers.Serializer):
    unsubscribed_from_all = serializers.BooleanField(required=False)

    def get_configuration(self):
        request = self.context.get("request", None)
        if request and request.user.is_authenticated:
            return NotificationBase.get_mapped_user_notifications_types_and_categories(request.user)
        return None

    def to_representation(self, obj):
        result = {
            "unsubscribed_from_all": obj.unsubscribed_from_all,
            "labels": {}
        }

        configuration = self.get_configuration()
        if configuration:
            for ntype, ntype_configuration in configuration.items():
                type_unsubscribed = set(obj.unsubscribed.get(ntype, []))
                result["labels"][ntype] = {}
                result[ntype] = {
                    "unsubscribed_from_all": "all" in type_unsubscribed
                }
                for key in ntype_configuration:
                    result[ntype][key] = key not in type_unsubscribed
                    result["labels"][ntype][key] = settings.UNIVERSAL_NOTIFICATIONS_CATEGORIES[ntype][key]

        return result

    def validate(self, data):
        """ validation actually maps categories data & adds them to validated data"""
        request = self.context.get("request", None)
        unsubscribed = {}
        data["unsubscribed"] = unsubscribed

        configuration = self.get_configuration()
        if configuration:
            for ntype, ntype_configuration in configuration.items():
                unsubscribed[ntype] = []
                if ntype in request.data:
                    for key in ntype_configuration:
                        if not request.data[ntype].get(key, True):
                            unsubscribed[ntype].append(key)
                        if request.data[ntype].get("unsubscribed_from_all", False):
                            unsubscribed[ntype].append("all")

        return data

    def update(self, instance, data):
        for key, value in data.items():
            setattr(instance, key, value)
        return instance
