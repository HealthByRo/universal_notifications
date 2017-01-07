# universal_notifications

[![build-status-image]][travis]
[![pypi-version]][pypi]
[![coverage-status-image]][codecov]

**High-level framework for notifications**

This project is intended to provide a convenient way to send notifications using multiple notification backends (e.g., e-mail, SMS, push).

---
## Setting up
To start using **universal_notifications** please add `universal_notifications` to `INSTALLED_APPS` in your Django project, and then migrate the app: `./manage.py migrate universal_notifications`. 

## Basic usage
* [WebSocket notifications](#websocket-notifications)
* [E-mail notifications](#e-mail-notifications)
* [SMS notifications](#sms-notifications)
* [Push notifications](#push-notifications)

### WebSocket notifications
``` python
class OrderShippedWS(WSNotification):
    message = 'order_shipped'
    serializer_class = OrderSerializer
    
# ... somewhere in a view
OrderShippedWS(item=order, receivers=[user], context={}).send()
```
### E-mail notifications
``` python
class OrderShippedEmail(EmailNotification):
    email_name = 'order_shipped'
    email_subject = _('{{user.full_name}}, Your order no. {{item.pk}} has been shipped.')

# ... somewhere in a view
OrderShippedEmail(item=order, receivers=[user], context={'user': user}).send()
```
E-mail notifications allow filtering e-mail addreses which are unsubscribed from receiving e-mails from your service. This can be achievied by setting the `UNIVERSAL_NOTIFICATIONS_UNSUBSCRIBED_MODEL` property in your project's settings.

Sample **UnsubscribedModel** should at least contain the **email** property. As result, all addresses existing in **UnsubscribedModel** objects will not receive any e-mails.

### SMS notifications
``` python
class OrderShippedSMS(SMSNotification):
    message = _('{{user.full_name}}, Your order no. {{item.pk}} has been shipped.')
               
    def prepare_receivers(self):
        return {x.shipping_address.phone for x in self.receivers}
        
# ... somewhere in a view
OrderShippedSMS(item=order, receivers=[user], context={'user': user}).send()
```

This feature requires setting the `UNIVERSAL_NOTIFICATIONS_SMS_FUNC` property in project's settings.

Sample **sms_send** function using [SMSAPI](https://github.com/smsapi/smsapi-python-client)
``` python
def send_sms(to_number, text, media=None, priority=9999):
    api.service('sms').action('send')
    api.set_content(text)
    api.set_to(to_number)
    api.execute()
```

### Push notifications
First of all, to use push notifications, you must provide a list of available **devices** linked to users. For more information, please check out [sources](https://github.com/ArabellaTech/universal_notifications/blob/master/universal_notifications/models.py#L20).

Supported platforms:
* [FCM](https://firebase.google.com/docs/cloud-messaging/) - Android, iOS, Web
* [GCM](https://developers.google.com/cloud-messaging/) - Android, iOS, Web
* [APNS](https://developer.apple.com/notifications/) - iOS

To make push notifications work on all supported platforms, a few properties need to be set:
* UNIVERSAL_NOTIFICATIONS_FCM_API_KEY - Firebase API key
* UNIVERSAL_NOTIFICATIONS_GCM_API_KEY - Google Cloud Messaging API key
* UNIVERSAL_NOTIFICATIONS_GCM_POST_URL - Google Cloud Messaging post url
* UNIVERSAL_NOTIFICATIONS_MOBILE_APPS[app_id]
    * APNS_CERTIFICATE - APNS certificate file
    * APNS_HOST
    * APNS_PORT
    * APNS_FEEDBACK_HOST
    * APNS_FEEDBACK_PORT
    * APNS_ERROR_TIMEOUT
    * APNS_MAX_NOTIFICATION_SIZE
    
Simple example of use:
``` python
class OrderShippedPush(PushNotification):
    message = _('{{user.full_name}}, Your order no. {{item.pk}} has been shipped.')
    
# ... somewhere in a view
OrderShippedPush(item=order, receivers=[user], context={'user': user}).send()
```

[coverage-status-image]: https://img.shields.io/codecov/c/github/ArabellaTech/universal_notifications/master.svg
[codecov]: http://codecov.io/github/ArabellaTech/universal_notifications?branch=master
[build-status-image]: https://secure.travis-ci.org/ArabellaTech/universal_notifications.svg?branch=master
[travis]: http://travis-ci.org/ArabellaTech/universal_notifications?branch=master
[pypi]: https://pypi.python.org/pypi/universal_notifications
[pypi-version]: https://img.shields.io/pypi/v/universal_notifications.svg
