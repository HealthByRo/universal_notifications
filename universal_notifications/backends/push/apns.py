"""
Apple Push Notification Service
Documentation is available on the iOS Developer Library:
https://developer.apple.com/library/ios/documentation/NetworkingInternet/Conceptual/RemoteNotificationsPG/Chapters/ApplePushService.html
"""

import json
import socket
import ssl
import struct
import time
from binascii import unhexlify
from contextlib import closing

from django.core.exceptions import ImproperlyConfigured
from push_notifications import NotificationError
from push_notifications.settings import PUSH_NOTIFICATIONS_SETTINGS as SETTINGS
from universal_notifications.backends.push.utils import get_app_settings


class APNSError(NotificationError):
    pass


class APNSServerError(APNSError):
    def __init__(self, status, identifier):
        super(APNSServerError, self).__init__(status, identifier)
        self.status = status
        self.identifier = identifier


class APNSDataOverflow(APNSError):
    pass


def _apns_create_socket(address_tuple, app_id):
    app_settings = get_app_settings(app_id)
    if not app_settings:
        raise ImproperlyConfigured('You need to set UNIVERSAL_NOTIFICATIONS_MOBILE_APPS[app_id]'
                                   ' to send messages through APNS')

    certfile = app_settings.get("APNS_CERTIFICATE")
    if not certfile:
        raise ImproperlyConfigured(
            'You need to set UNIVERSAL_NOTIFICATIONS_MOBILE_APPS[app_id]["APNS_CERTIFICATE"] '
            'to send messages through APNS.'
        )

    try:
        with open(certfile, "r") as f:
            f.read()
    except Exception as e:
        raise ImproperlyConfigured("The APNS certificate file at %r is not readable: %s" % (certfile, e))

    sock = socket.socket()
    sock = ssl.wrap_socket(sock, ssl_version=ssl.PROTOCOL_TLSv1, certfile=certfile)
    sock.connect(address_tuple)

    return sock


def _apns_create_socket_to_push(app_id):
    return _apns_create_socket((SETTINGS["APNS_HOST"], SETTINGS["APNS_PORT"]), app_id)


def _apns_pack_frame(token_hex, payload, identifier, expiration, priority):
    token = unhexlify(token_hex)
    # |COMMAND|FRAME-LEN|{token}|{payload}|{id:4}|{expiration:4}|{priority:1}
    frame_len = 3 * 5 + len(token) + len(payload) + 4 + 4 + 1  # 5 items, each 3 bytes prefix, then each item length
    frame_fmt = "!BIBH%ssBH%ssBHIBHIBHB" % (len(token), len(payload))
    frame = struct.pack(
        frame_fmt,
        2, frame_len,
        1, len(token), token,
        2, len(payload), payload,
        3, 4, identifier,
        4, 4, expiration,
        5, 1, priority)

    return frame


def _apns_check_errors(sock):
    timeout = SETTINGS["APNS_ERROR_TIMEOUT"]
    if timeout is None:
        return  # assume everything went fine!
    saved_timeout = sock.gettimeout()
    try:
        sock.settimeout(timeout)
        data = sock.recv(6)
        if data:
            command, status, identifier = struct.unpack("!BBI", data)
            # apple protocol says command is always 8. See http://goo.gl/ENUjXg
            assert command == 8, "Command must be 8!"
            if status != 0:
                raise APNSServerError(status, identifier)
    except socket.timeout:  # py3, see http://bugs.python.org/issue10272
        pass
    except ssl.SSLError as e:  # py2
        if "timed out" not in e.message:
            raise
    except AttributeError:
        pass
    finally:
        sock.settimeout(saved_timeout)


def _apns_send(app_id, token, alert, badge=None, sound=None, category=None, content_available=False,
               action_loc_key=None, loc_key=None, loc_args=[], extra={}, identifier=0,
               expiration=None, priority=10, socket=None):
    data = {}
    aps_data = {}

    if action_loc_key or loc_key or loc_args:
        alert = {"body": alert} if alert else {}
        if action_loc_key:
            alert["action-loc-key"] = action_loc_key
        if loc_key:
            alert["loc-key"] = loc_key
        if loc_args:
            alert["loc-args"] = loc_args

    if alert is not None:
        aps_data["alert"] = alert

    if badge is not None:
        aps_data["badge"] = badge

    if sound is not None:
        aps_data["sound"] = sound

    if category is not None:
        aps_data["category"] = category

    if content_available:
        aps_data["content-available"] = 1

    data["aps"] = aps_data
    data.update(extra)

    # convert to json, avoiding unnecessary whitespace with separators (keys sorted for tests)
    json_data = json.dumps(data, separators=(",", ":"), sort_keys=True).encode("utf-8")

    max_size = SETTINGS["APNS_MAX_NOTIFICATION_SIZE"]
    if len(json_data) > max_size:
        raise APNSDataOverflow("Notification body cannot exceed %i bytes" % (max_size))

    # if expiration isn't specified use 1 month from now
    expiration_time = expiration if expiration is not None else int(time.time()) + 2592000

    frame = _apns_pack_frame(token, json_data, identifier, expiration_time, priority)

    if socket:
        socket.write(frame)
    else:
        with closing(_apns_create_socket_to_push(app_id)) as socket:
            socket.write(frame)
            _apns_check_errors(socket)


def apns_send_message(device, message=None, data=None):
    """
    Sends an APNS notification to a single registration_id.
    This will send the notification as form data.

    Note that if set message should always be a string. If it is not set,
    it won't be included in the notification. You will need to pass None
    to this for silent notifications.
    """
    _apns_send(device.app_id, device.notification_token, message, **data)
