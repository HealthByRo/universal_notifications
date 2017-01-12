# universal_notifications


To have Universal Notifications receive WS notifications (ie. to mark notification as received) add to your settings.py:

::

    WS4REDIS_SUBSCRIBER = 'universal_notifications.backend.websockets.RedisSubscriber'

