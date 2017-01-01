# -*- coding: utf-8 -*-
from django.contrib import admin
from universal_notifications.models import NotificationHistory


class NotificationHistoryAdmin(admin.ModelAdmin):
    list_display = ('receiver', 'created', 'group', 'klass', 'details')
    readonly_fields = ('receiver', 'created', 'group', 'klass', 'details')


admin.site.register(NotificationHistory, NotificationHistoryAdmin)
