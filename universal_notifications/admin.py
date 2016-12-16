# -*- coding: utf-8 -*-
from universal_notifications.models import NotificationHistory

from django.contrib import admin


class NotificationHistoryAdmin(admin.ModelAdmin):
    list_display = ('receiver', 'created', 'group', 'klass', 'details')
    readonly_fields = ('receiver', 'created', 'group', 'klass', 'details')


admin.site.register(NotificationHistory, NotificationHistoryAdmin)
