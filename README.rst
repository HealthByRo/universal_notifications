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

If you intend to use any other type of notification than WS, then UNIVERSAL_NOTIFICATIONS_CATEGORIES
must be defined (see `Unsubscriber`_)

Basic usage
-----------
-  `WebSocket notifications`_
-  `E-mail notifications`_
-  `SMS notifications`_
-  `Push notifications`_
-  `Unsubscriber`_

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

Unsubscriber
~~~~~~~~~~~~~~~~~

This section refers to all notifications except WebSockets, which by default are not prone to unsubscriptions
(however this can be changed by setting check_subscription to True).

Each category for each type must be explicitly declared in config (with label). If it is not there, exception
will be raised on attempt to send such notification. This requirement is to prevent situation, that notification
of given type is send to user who would not wish to receive it, but cannot unsubscribe from it (since it is not
present in the config).

Since categories can be changed with configuration, labels should be specified for them, since they can't be
hardcoded in client's app.

There is one special category: "system". This category should not be declared in configuration, and notification
with such category will always pass.

Sample configuration:

.. code:: python

        UNIVERSAL_NOTIFICATIONS_CATEGORIES={
            "push": {
                "default": _("This is a label for default category you'll send to FE"),
                "chat": _('Category for chat messages'),
                "promotions": _('Promotions',)
            },
            "email": {
                "default": _("This is a label for default category you'll send to FE"),
                "chat": _('Category for chat messages'),
                "newsletter": _('Newsletter',)
            },
            "sms": {
                "default": _("This is a label for default category you'll send to FE"),
                "chat": _('Category for chat messages'),
                "newsletter": _('Newsletter',)
            },
            "test": {
                "default": _("This is a label for default category you'll send to FE"),
            },
        },

If you want to allow different types of users to have different categories of notifications, you can
do it with configuration:

.. code:: python

        # not required. If defined, specific types of users will only get notifications from allowed categories.
        # requires a bit more configuration - helper function to check if notification category is allowed for user
        UNIVERSAL_NOTIFICATIONS_USER_CATEGORIES_MAPPING={
            "for_admin": {
                "push": ["default", "chat", "promotions"],
                "email": ["default", "chat", "newsletter"],
                "sms": ["default", "chat", "newsletter"]
            },
            "for_user": {
                "push": ["default", "chat", "promotions"],
                "email": ["default", "newsletter"],  # chat skipped
                "sms": ["default", "chat", "newsletter"]
            }
        },
        # path to the file we will import user definitions for UNIVERSAL_NOTIFICATIONS_USER_CATEGORIES_MAPPING
        UNIVERSAL_NOTIFICATIONS_USER_DEFINITIONS_FILE='tests.user_conf'

        # from file: tests/user_conf.py
        def for_admin(user):
            return user.is_superuser


        def for_user(user):
            return not user.is_superuser

In the example above, functions "for_admin" & "for_user" should be defined in file tests/user_conf.py. Each
function takes user as a parameter, and should return either True or False.

If given notification type is not present for given user, user will neither be able to receive it nor unsubscribe it.
