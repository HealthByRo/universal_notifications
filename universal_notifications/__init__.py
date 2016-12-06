# -*- coding: utf-8 -*-
from universal_notifications.notifications import EmailNotification
from universal_notifications.notifications import PushNotification
from universal_notifications.notifications import SMSNotification
from universal_notifications.notifications import WSNotification

__title__ = 'Universal Notification'
__version__ = '0.3.0'
__author__ = 'Pawel Krzyzaniak'
__license__ = 'Proprietary'
__copyright__ = 'Copyright 2016 Arabella'

# Version synonym
VERSION = __version__


__all__ = ['WSNotification', 'SMSNotification', 'EmailNotification', 'PushNotification']
