# -*- coding: utf-8 -*-
"""
    Helper file. Contains user configuration for user categories mapping.
    Usage: settings.UNIVERSAL_NOTIFICATIONS_USER_DEFINITIONS_FILE
"""


def for_admin(user):
    return user.is_superuser


def for_user(user):
    return not user.is_superuser
