"""
    Helper file. Contains user configuration for user categories mapping.
    This file has to be imported with * (sadly)
"""


def for_admin(user):
    return user.is_superuser


def for_user(user):
    return not user.is_superuser
