universal\_notifications
========================
|travis|_ |pypi|_ |codecov|_ |requiresio|_

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
-  `Unsubscriber API`_
-  `FakeEmailSend view`_

WebSocket notifications
~~~~~~~~~~~~~~~~~~~~~~~

To have Universal Notifications receive WS notifications (ie. to mark notification as received)
add to your settings.py:

::

    WS4REDIS_SUBSCRIBER = 'universal_notifications.backends.websockets.RedisSignalSubscriber'

Upon receiving a WS, "ws_received" signal will be emitted with json data received in the message, and all emails
subscribed to that channel. Sample usage:

.. code:: python

    from universal_notifications.signals import ws_received

    def your_handler(sender, message_data, channel_emails, **kwargs):
        pass
    ws_received.connect(your_handler)

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

Settings
    * UNIVERSAL_NOTIFICATIONS_IS_SECURE (bool, default: False) - set https protocol and `is_secure` variable
    * UNIVERSAL_NOTIFICATIONS_USE_PREMAILER (bool, default: True) - use premailer to append CSS styles inline (speedup tests a lot when False)


SMS notifications
~~~~~~~~~~~~~~~~~

Supported platforms:
 * `Twilio <https://www.twilio.com/>`_ - default engine
 * `AmazonSNS <https://aws.amazon.com/sns/>`_

Settings
    * UNIVERSAL_NOTIFICATIONS_SMS_ENGINE - set engine
    * UNIVERSAL_NOTIFICATIONS_VALIDATE_MOBILE (bool)

Engine settinsgs:
    * Twilio
        * UNIVERSAL_NOTIFICATIONS_TWILIO_API_ENABLED (bool)
        * UNIVERSAL_NOTIFICATIONS_TWILIO_ENABLE_PROXY (bool)
        * UNIVERSAL_NOTIFICATIONS_TWILIO_ACCOUNT (string)
        * UNIVERSAL_NOTIFICATIONS_TWILIO_TOKEN (string)
        * UNIVERSAL_NOTIFICATIONS_TWILIO_REPORT_ERRORS (list of integers)
    * Amazon SNS
        * UNIVERSAL_NOTIFICATIONS_AMAZON_SNS_API_ENABLED (bool)
        * AWS_ACCESS_KEY_ID (string)
        * AWS_SECRET_ACCESS_KEY (string)
        * AWS_DEFAULT_REGION (string) - default us-east-1


Simple example of use:

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

.. |requiresio| image:: https://requires.io/github/ArabellaTech/universal_notifications/requirements.svg?branch=requires-io-master
.. _requiresio: https://requires.io/github/ArabellaTech/universal_notifications/requirements/?branch=requires-io-master

Unsubscriber
~~~~~~~~~~~~

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

Unsubscriber API
~~~~~~~~~~~~~~~~

The current subscriptions can be obtained with a API described below. Please note, that API does not provide label for "unsubscribe_from_all", since is always present and can be hardcoded in FE module. Categories however may vary, that's why labels for them must be returned from BE.

.. code:: python

        # GET /subscriptions

        return {
            "unsubscribe_from_all": bool,  # False by default
            "each_type_for_given_user": {
                "each_category_for_given_type_for_given_user": bool,  # True(default) if subscribed, False if unsubscribed
                "unsubscribe_from_all": bool  # False by default
            }
            "labels": {
                "each_type_for_given_user": {
                    "each_category_for_given_type_for_given_user": string,
                }
            }
        }

Unsubscriptions may be edited using following API:

.. code:: python

        # PUT /subscriptions

        data = {
            "unsubscribe_from_all": bool,  # False by default
            "each_type_for_given_user": {
                "each_category_for_given_type_for_given_user": bool,  # True(default) if subscribed, False if unsubscribed
                "unsubscribe_from_all": bool  # False by default
            }
        }

Please note, that if any type/category for type is ommited, it is reseted to default value.

FakeEmailSend view
~~~~~~~~~~~~~~~~~~
**universal_notifications.backends.emails.views.FakeEmailSend** is a view that helps testing email templates.
To start using it, add ``url(r'^emails/', include('universal_notifications.backends.emails.urls'))``
to your urls.py, and specify receiver email address using ``UNIVERSAL_NOTIFICATIONS_FAKE_EMAIL_TO``.

After that you can make a request to the new url with **template** parameter, for instance:
``http://localhost:8000/emails/?template=reset_password``, which  will send an email using
``emails/email_reset_password.html`` as the template.
