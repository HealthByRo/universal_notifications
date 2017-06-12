# -*- coding: utf-8 -*-
import json

from django.conf import settings
from rest_framework.renderers import JSONRenderer
from universal_notifications.tasks import ws_received_send_signal_task
from ws4redis.publisher import RedisPublisher
from ws4redis.redis_store import RedisMessage
from ws4redis.subscriber import RedisSubscriber


def publish(user, item=None, additional_data=None):
    if additional_data is None:
        additional_data = {}
    redis_publisher = RedisPublisher(facility='all', users=[user.email])
    r = JSONRenderer()
    if item is None:
        data = {}
    else:
        data = item.as_dict()
    data.update(additional_data)
    data = r.render(data)
    message = RedisMessage(data)
    if getattr(settings, 'TESTING', False):
        # Do not send in tests
        return
    redis_publisher.publish_message(message)


class RedisSignalSubscriber(RedisSubscriber):
    def publish_message(self, message, expire=None):
        try:
            message_data = json.loads(message)
            # I didn't found any better way to dig out who is subscribed to a given channel (not to mention who
            # just have send the given message). User ID can be passed in message, however this opens a hole in the
            # system, so - as long as we've only per-user channels (opened with a auth token), it should be safe to
            # use email of those users to identify the user.
            channel_emails = [str(x).split(":")[2] for x in self._subscription.channels.keys()]

            ws_received_send_signal_task.apply_async(args=[message_data, channel_emails])
        except Exception:
            # I mean it, catch everything, log it if needed but do catch everything
            pass
        return super(RedisSignalSubscriber, self).publish_message(message, expire)
