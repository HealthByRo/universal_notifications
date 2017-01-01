# Send to single device.
from pyfcm import FCMNotification
from universal_notifications.backends.push.utils import get_app_settings


def fcm_send_message(device, message, data=None):
    app_settings = get_app_settings(device.app_id)
    api_key = app_settings.get('FCM_API_KEY')
    if not app_settings or not api_key:
        return

    push_service = FCMNotification(api_key=api_key)
    return push_service.notify_single_device(
        registration_id=device.notification_token,
        message_body=message,
        data_message=data
    )
