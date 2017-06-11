# -*- coding: utf-8 -*-
from django.contrib import admin
from universal_notifications.models import (NotificationHistory, Phone, PhoneReceived, PhoneReceivedRaw, PhoneReceiver,
                                            PhoneSent, UnsubscribedUser)

# TODO: think about adding django-safedelete


class NotificationHistoryAdmin(admin.ModelAdmin):
    list_display = ("receiver", "created", "group", "klass", "details")
    readonly_fields = ("receiver", "created", "group", "klass", "details")


class PhoneSentAdmin(admin.ModelAdmin):
    list_display = ("created", "sms_id", "status", "updated", "error_message")
    raw_id_fields = ("receiver",)
    search_fields = ("receiver__number",)


class PhoneReceivedAdmin(admin.ModelAdmin):
    list_display = ("sms_id", "created", "updated")
    raw_id_fields = ("receiver", "raw")


class PhoneReceivedRawAdmin(admin.ModelAdmin):
    list_display = ("created", "status",)


class PhoneReceiverAdmin(admin.ModelAdmin):
    list_display = ("number", "service_number", "is_blocked")


class PhoneAdmin(admin.ModelAdmin):
    list_display = ("number", "used_count")
    readonly_fields = ("used_count",)


admin.site.register(PhoneSent, PhoneSentAdmin)
admin.site.register(PhoneReceived, PhoneReceivedAdmin)
admin.site.register(PhoneReceivedRaw, PhoneReceivedRawAdmin)
admin.site.register(PhoneReceiver, PhoneReceiverAdmin)
admin.site.register(Phone, PhoneAdmin)
admin.site.register(UnsubscribedUser)
admin.site.register(NotificationHistory, NotificationHistoryAdmin)
