from django.conf import settings


def get_app_settings(app_id):
    return getattr(settings, "MOBILE_APPS", {}).get(app_id)
