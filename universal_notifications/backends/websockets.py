# -*- coding: utf-8 -*-
from django.conf import settings
from rest_framework.renderers import JSONRenderer
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


class RedisSubscriber(RedisSubscriber):
    def publish_message(self, message, expire=None):
        try:
            # custom code goes here
            # for efficiency think about using celery to do the job - has to be freaking FAST!
            print ('message received!')
            print ('message!')
        except Exception:
            # I mean it, catch everything, log it if needed but do catch everything
            pass
        return super(RedisSubscriber, self).publish_message(message, expire)
