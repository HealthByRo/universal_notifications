universal\_notifications
========================
|travis|_ |pypi|_ |codecov|_

**High-level framework for notifications**

This project is intended to provide a convenient way to send notifications using multiple
notification backends (e.g., e-mail, SMS, push).

--------------

Setting up
----------

To start using **universal\_notifications** please add ``universal_notifications`` to
``INSTALLED_APPS`` in your Django project, and then migrate the app:
``./manage.py migrate universal_notifications``.

Basic usage
-----------

-  `WebSocket notifications`_
-  `E-mail notifications`_
-  `SMS notifications`_
-  `Push notifications`_

WebSocket notifications
~~~~~~~~~~~~~~~~~~~~~~~

To have Universal Notifications receive WS notifications (ie. to mark notification as received)
add to your settings.py:

::

    WS4REDIS_SUBSCRIBER = 'universal_notifications.backend.websockets.RedisSubscriber'

Simple example of using WS notifications:

.. code:: python

    class OrderShippedWS(WSNotification):
        message = 'order_shipped'
        serializer_class = OrderSerializer

    # ... somewhere in a view
    OrderShippedWS(item=order, receivers=[user], context={}).send()

E-mail notifications
~~~~~~~~~~~~~~~~~~~~

.. code:: python

    class OrderShippedEmail(EmailNotification):
        email_name = 'order_shipped'
        email_subject = _('Order no. {{item.pk}} has been shipped.')

    # ... somewhere in a view
    OrderShippedEmail(item=order, receivers=[user], context={}).send()

E-mail notifications allow filtering e-mail addreses which are unsubscribed from receiving e-mails
from your service. This can be achievied by setting the
``UNIVERSAL_NOTIFICATIONS_UNSUBSCRIBED_MODEL`` property in your project’s settings.

Sample **UnsubscribedModel** should at least contain the **email** property. As result, all
addresses existing in **UnsubscribedModel** objects will not receive any e-mails.

SMS notifications
~~~~~~~~~~~~~~~~~

.. code:: python

    class OrderShippedSMS(SMSNotification):
        message = _('Order no. {{item.pk}} has been shipped.')

        def prepare_receivers(self):
            return {x.shipping_address.phone for x in self.receivers}

    # ... somewhere in a view
    OrderShippedSMS(item=order, receivers=[user], context={}).send(

Push notifications
~~~~~~~~~~~~~~~~~~

First of all, to use push notifications, you must provide a list of available **devices** linked to users.
For more information, please check out
`sources <https://github.com/ArabellaTech/universal_notifications/blob/master/universal_notifications/models.py#L20>`_.

Supported platforms:
 * `FCM <https://firebase.google.com/docs/cloud-messaging/>`_ - Android, iOS, Web
 * `GCM <https://firebase.google.com/docs/cloud-messaging/>`_ - Android, iOS, Web
 * `APNS <https://developer.apple.com/notifications/>`_ - iOS

To make push notifications work on all supported platforms, a few properties need to be set:
 * UNIVERSAL_NOTIFICATIONS_MOBILE_APPS[app_id]
    * APNS_CERTIFICATE - APNS certificate file
    * FCM_API_KEY - Firebase API key
    * GCM_API_KEY - Google Cloud Messaging API key
 * GCM_POST_URL - Google Cloud Messaging post url

Settings related to Apple Push Notification service:
 * APNS_HOST
 * APNS_PORT
 * APNS_FEEDBACK_HOST
 * APNS_FEEDBACK_PORT
 * APNS_ERROR_TIMEOUT
 * APNS_MAX_NOTIFICATION_SIZE

Simple example of use:

.. code:: python

    class OrderShippedPush(PushNotification):
        message = _('Order no. {{item.pk}} has been shipped.')

    # ... somewhere in a view
    OrderShippedPush(item=order, receivers=[user], context={}).send()

.. _WebSocket notifications: #websocket-notifications
.. _E-mail notifications: #e-mail-notifications
.. _SMS notifications: #sms-notifications
.. _Push notifications: #push-notifications
.. _SMSAPI: https://github.com/smsapi/smsapi-python-client

.. |travis| image:: https://secure.travis-ci.org/ArabellaTech/universal_notifications.svg?branch=master
.. _travis: http://travis-ci.org/ArabellaTech/universal_notifications?branch=master

.. |pypi| image:: https://img.shields.io/pypi/v/universal_notifications.svg
.. _pypi: https://pypi.python.org/pypi/universal_notifications

.. |codecov| image:: https://img.shields.io/codecov/c/github/ArabellaTech/universal_notifications/master.svg
.. _codecov: http://codecov.io/github/ArabellaTech/universal_notifications?branch=master
