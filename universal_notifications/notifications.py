# -*- coding: utf-8 -*-
"""
    # TODO: fill readme & TODO
    # TODO (Pawel): processors filtering (email/sms) - unsubscription, etc, mail/sms history + limiters
    # TODO (Pawel): sample transformations / conditions
    # TODO (Pawel): push (gcm, etc.) - low priority

    Sample usage:
        WSNotification(item, receivers, context).send()

    Chaining example:
        chaining = (
            {
                'class': PushNotification,  # required, must be a subclass of NotificationBase
                'delay': 0,  # required, [in seconds]
                'transform_func': None,  # optional, should take as parameters (item, receivers, context)
                                         # and return transformed item, receivers, context - see Transformations
                                         # if empty or missing - no transformation is applied
                'condition_func': None,  # optional, should take as parameters (item, receivers, context, parent_result)
                                         # and returns True if notification should be send and False if not
                                         # if function is None,
                },
        )
"""
from django.template import Context, Template
from universal_notifications.backends.emails import (UnsubscribedModel,
                                                     send_email)
from universal_notifications.backends.sms import send_sms
from universal_notifications.backends.websockets import publish
from universal_notifications.models import Device, NotificationHistory
from universal_notifications.tasks import process_chained_notification


class NotificationBase(object):
    chaining = None

    @classmethod
    def get_type(cls):
        raise NotImplementedError

    def __init__(self, item, receivers, context):
        self.item = item
        self.receivers = receivers
        self.context = context

    def prepare_receivers(self):
        raise NotImplementedError

    def prepare_message(self):
        raise NotImplementedError

    def send_inner(self, prepared_receivers, prepared_message):
        raise NotImplementedError

    def get_notification_history_details(self):
        raise NotImplementedError

    def format_receiver_for_notification_history(self, receiver):
        return receiver

    def save_notifications(self, prepared_receivers):
        for receiver in prepared_receivers:
            NotificationHistory.objects.create(
                group=self.get_type(),
                klass=self.__class__.__name__,
                receiver=self.format_receiver_for_notification_history(receiver),
                details=self.get_notification_history_details()
            )

    def send(self):
        prepared_receivers = self.prepare_receivers()
        prepared_message = self.prepare_message()
        result = self.send_inner(prepared_receivers, prepared_message)
        self.save_notifications(prepared_receivers)
        if self.chaining:
            for conf in self.chaining:
                args = [conf, self.item, self.receivers, self.context, result]
                if conf['delay'] > 0:
                    process_chained_notification.apply_async(args, countdown=conf['delay'])
                else:  # no delay, so execute function directly, not as task
                    process_chained_notification(*args)
        return result


class WSNotification(NotificationBase):
    message = None  # required
    serializer_class = None  # required, DRF serializer
    serializer_many = False

    def prepare_receivers(self):
        return set(self.receivers)

    def prepare_message(self):
        return {
            'message': self.message,
            'data': self.serializer_class(self.item, context=self.context, many=self.serializer_many).data
        }

    def format_receiver_for_notification_history(self, receiver):
        return receiver.email

    def send_inner(self, prepared_receivers, prepared_message):
        for receiver in prepared_receivers:
            publish(receiver, additional_data=prepared_message)

    def get_notification_history_details(self):
        return "message: %s, serializer: %s" % (self.message, self.serializer_class.__name__)

    @classmethod
    def get_type(cls):
        return "WebSocket"


class SMSNotification(NotificationBase):
    message = None  # required, django template string

    def prepare_receivers(self):
        return {x.phone for x in self.receivers}

    def prepare_message(self):
        return Template(self.message).render(Context({"item": self.item}))

    def send_inner(self, prepared_receivers, prepared_message):
        for receiver in prepared_receivers:
            send_sms(receiver, prepared_message)

    def get_notification_history_details(self):
        return self.prepare_message()

    @classmethod
    def get_type(cls):
        return "SMS"


class EmailNotification(NotificationBase):
    email_name = None  # required
    email_subject = None  # required

    @classmethod
    def format_receiver(cls, receiver):
        return "%s %s <%s>" % (receiver.first_name, receiver.last_name, receiver.email)

    def prepare_receivers(self):
        result = set()
        if UnsubscribedModel:
            unsubscribed_emails = UnsubscribedModel.objects.filter(
                email__in=(receiver.email for receiver in self.receivers)
            )
            unsubscribed_emails = set(unsubscribed_emails.values_list('email', flat=True))
        else:
            unsubscribed_emails = set()
        for receiver in self.receivers:
            if receiver.email not in unsubscribed_emails:
                result.add(receiver)
        return result

    def prepare_message(self):
        return {
            'item': self.item,
        }

    def format_receiver_for_notification_history(self, receiver):
        return receiver.email

    def prepare_subject(self):
        return Template(self.email_subject).render(Context({"item": self.item}))

    def send_inner(self, prepared_receivers, prepared_message):
        prepared_subject = self.prepare_subject()
        for receiver in prepared_receivers:
            prepared_message['receiver'] = receiver
            send_email(self.email_name, self.format_receiver(receiver), prepared_subject, prepared_message)

    def get_notification_history_details(self):
        return self.email_name

    @classmethod
    def get_type(cls):
        return "Email"


class PushNotification(NotificationBase):
    message = None  # required, django template string

    @classmethod
    def get_type(cls):
        return "Push"

    def prepare_receivers(self):
        return set(self.receivers)

    def prepare_body(self):  # self.item & self.context can be used here
        return {}

    def prepare_message(self):
        return {
            'message': Template(self.message).render(Context({"item": self.item})),
            'data': self.prepare_body()
        }

    def format_receiver_for_notification_history(self, receiver):
        return receiver.email

    def send_inner(self, prepared_receivers, prepared_message):  # TODO
        for receiver in prepared_receivers:
            for d in Device.objects.filter(user=receiver, is_active=True):
                d.send_message(prepared_message["message"], **prepared_message["data"])

    def get_notification_history_details(self):
        return self.prepare_message()
