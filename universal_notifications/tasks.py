# -*- coding: utf-8 -*-
# TODO: make it somehow configurable
from getreferd.celery import app


@app.task()
def process_chained_notification(conf, item, receivers, context, parent_result):
    """ conf - configuration of chained notification
        item, receivers, context - parameters for creating Notification subclass
        parent result - result of sending parent notification """

    notification_class = conf['class']
    transform_func = conf.get('transform_func', None)
    condition_func = conf.get('condition_func', None)

    # parameters transformation
    if transform_func:
        item, receivers, context = transform_func(item, receivers, context)

    # checking if notification should be skipped
    if condition_func:
        if not condition_func(item, receivers, context, parent_result):
            return

    # sending out notification
    notification_class(item, receivers, context).send()
