"""
Google Cloud Messaging
Previously known as C2DM
Documentation is available on the Android Developer website:
https://developer.android.com/google/gcm/index.html
"""

import json

from push_notifications import NotificationError
from push_notifications.settings import PUSH_NOTIFICATIONS_SETTINGS as SETTINGS
from universal_notifications.backends.push.utils import get_app_settings

try:
    from urllib.request import Request, urlopen
    from urllib.parse import urlencode
except ImportError:
    # Python 2 support
    from urllib2 import Request, urlopen
    from urllib import urlencode


class GCMError(NotificationError):
    pass


def _chunks(l, n):
    """
    Yield successive chunks from list \a l with a minimum size \a n
    """
    for i in range(0, len(l), n):
        yield l[i:i + n]


def _gcm_send(app_id, data, content_type):
    app_settings = get_app_settings(app_id)
    key = app_settings.get('GCM_API_KEY')
    if not app_settings or key:
        return

    headers = {
        "Content-Type": content_type,
        "Authorization": "key=%s" % (key),
        "Content-Length": str(len(data)),
    }

    request = Request(SETTINGS["GCM_POST_URL"], data, headers)
    return urlopen(request).read()


def _gcm_send_plain(device, data, collapse_key=None, delay_while_idle=False, time_to_live=0):
    """
    Sends a GCM notification to a single registration_id.
    This will send the notification as form data.
    If sending multiple notifications, it is more efficient to use
    gcm_send_bulk_message() with a list of registration_ids
    """

    values = {"registration_id": device.notification_token}

    if collapse_key:
        values["collapse_key"] = collapse_key

    if delay_while_idle:
        values["delay_while_idle"] = int(delay_while_idle)

    if time_to_live:
        values["time_to_live"] = time_to_live

    for k, v in data.items():
        values["data.%s" % (k)] = v.encode("utf-8")

    data = urlencode(sorted(values.items())).encode("utf-8")  # sorted items for tests

    result = _gcm_send(device.app_id, data, "application/x-www-form-urlencoded;charset=UTF-8")
    if result.startswith("Error="):
        raise GCMError(result)
    return result


def _gcm_send_json(device, data, collapse_key=None, delay_while_idle=False, time_to_live=0):
    """
    Sends a GCM notification to one or more registration_ids. The registration_ids
    needs to be a list.
    This will send the notification as json data.
    """

    values = {"registration_ids": [device.notification_token]}

    if data is not None:
        values["data"] = data

    if collapse_key:
        values["collapse_key"] = collapse_key

    if delay_while_idle:
        values["delay_while_idle"] = delay_while_idle

    if time_to_live:
        values["time_to_live"] = time_to_live

    data = json.dumps(values, separators=(",", ":"), sort_keys=True).encode("utf-8")  # keys sorted for tests
    result = _gcm_send(device.app_id, data, "application/json")
    if result:
        result = json.loads(result)
        if result["failure"]:
            raise GCMError(result)
    return result


def gcm_send_message(device, message, data=None, collapse_key=None, delay_while_idle=False, time_to_live=0):
    """
    Sends a GCM notification to a single registration_id.

    This will send the notification as form data if possible, otherwise it will
    fall back to json data.
    """
    data["message"] = message
    args = data, collapse_key, delay_while_idle, time_to_live
    try:
        try:
            return _gcm_send_plain(device, *args)
        except AttributeError:
            return _gcm_send_json(device, *args)
    except GCMError:
        # TODO: check error and maybe deactivate user
        return False
