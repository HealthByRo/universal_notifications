# -*- coding: utf-8 -*-
"""Universal Notifications

Sample usage:
    WSNotification(item, receivers, context).send()

Chaining example:
    chaining = (
        {
            "class": PushNotification,  # required, must be a subclass of NotificationBase
            "delay": 0,  # required, [in seconds]
            "transform_func": None,  # optional, should take as parameters (item, receivers, context)
                                     # and return transformed item, receivers, context - see Transformations
                                     # if empty or missing - no transformation is applied
            "condition_func": None,  # optional, should take as parameters (item, receivers, context, parent_result)
                                     # and returns True if notification should be send and False if not
                                     # if function is None,
            },
    )
"""
import importlib
import logging
import re
from email.utils import formataddr

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.models import Site
from django.core.exceptions import ImproperlyConfigured
from django.core.mail import EmailMessage
from django.template import Context, Template
from django.template.loader import get_template
from premailer import Premailer
from universal_notifications.backends.sms.utils import send_sms
from universal_notifications.backends.websockets import publish
from universal_notifications.models import Device, NotificationHistory, UnsubscribedUser
from universal_notifications.tasks import process_chained_notification

logger = logging.getLogger(__name__)

user_definitions = None
if hasattr(settings, "UNIVERSAL_NOTIFICATIONS_USER_DEFINITIONS_FILE") and \
        hasattr(settings, "UNIVERSAL_NOTIFICATIONS_USER_CATEGORIES_MAPPING"):
    user_definitions = importlib.import_module(settings.UNIVERSAL_NOTIFICATIONS_USER_DEFINITIONS_FILE)


class NotificationBase(object):
    chaining = None
    check_subscription = True
    category = "default"
    PRIORITY_CATEGORY = "system"  # this category will be always sent

    @classmethod
    def get_type(cls):
        raise NotImplementedError

    def __init__(self, item, receivers, context=None):
        self.item = item
        self.receivers = receivers
        self.context = context or {}

    @classmethod
    def get_mapped_user_notifications_types_and_categories(cls, user):
        """Returns a dictionary for given user type:

        {"notificaiton_type": [categries list]}
        TODO: use this one in serializer.
        """
        if not hasattr(settings, "UNIVERSAL_NOTIFICATIONS_USER_CATEGORIES_MAPPING"):
            notifications = {}
            for key in settings.UNIVERSAL_NOTIFICATIONS_CATEGORIES.keys():
                notifications[key] = settings.UNIVERSAL_NOTIFICATIONS_CATEGORIES[key].keys()
            return notifications
        else:
            for user_type in settings.UNIVERSAL_NOTIFICATIONS_USER_CATEGORIES_MAPPING:
                if getattr(user_definitions, user_type)(user):
                    return settings.UNIVERSAL_NOTIFICATIONS_USER_CATEGORIES_MAPPING[user_type]

    def get_user_categories_for_type(self, user):
        """Check categories available for given user type and this notification type.

        If no mapping present we assume all are allowed.
        Raises ImproperlyConfigured if no categories for given user availaible
        """
        categories = self.get_mapped_user_notifications_types_and_categories(user)
        if categories:
            return categories[self.get_type().lower()]

        raise ImproperlyConfigured(
            "UNIVERSAL NOTIFICATIONS USER CATEGORIES MAPPING: No categories for given user: %s" % user)

    def get_context(self):
        context = self.context
        context["item"] = self.item
        return context

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

    def check_category(self):
        if self.category == self.PRIORITY_CATEGORY or not self.check_subscription:
            return
        if not self.category:
            raise ImproperlyConfigured("Category is required", self)

        notification_type = self.get_type().lower()
        if not hasattr(settings, "UNIVERSAL_NOTIFICATIONS_CATEGORIES"):
            raise ImproperlyConfigured("Please define UNIVERSAL_NOTIFICATIONS_CATEGORIES in your settings.py")

        categories = settings.UNIVERSAL_NOTIFICATIONS_CATEGORIES.get(notification_type, {})
        if self.category not in categories.keys():
            raise ImproperlyConfigured("No such category for Universal Notifications: %s: %s." % (
                self.get_type(), self.category))
        # check if user is allowed to get notifications from this category
        for user in self.receivers:
            if self.category not in self.get_user_categories_for_type(user):
                raise ImproperlyConfigured(
                    "User is not allowed to receive notifications from '%s:%s' category"
                    % (self.get_type(), self.category))

    def verify_and_filter_receivers_subscriptions(self):
        """Returns new list of only receivers that are subscribed for given notification type/category."""
        if not self.check_subscription or self.category == self.PRIORITY_CATEGORY:
            return self.receivers

        receivers_ids = (x.id for x in self.receivers)
        unsubscribed_map = {}
        for unsubscribed_user in UnsubscribedUser.objects.filter(user__in=receivers_ids):
            unsubscribed_map[unsubscribed_user.user_id] = unsubscribed_user

        filtered_receivers = []
        ntype = self.get_type().lower()
        for receiver in self.receivers:
            unsubscribed_user = unsubscribed_map.get(receiver.id, None)
            if unsubscribed_user:
                if unsubscribed_user.unsubscribed_from_all:
                    continue
                unsubscribed = unsubscribed_user.unsubscribed.get(ntype, {})
                if "all" in unsubscribed or self.category in unsubscribed:
                    continue
            filtered_receivers.append(receiver)
        self.receivers = filtered_receivers

    def save_notifications(self, prepared_receivers):
        for receiver in prepared_receivers:
            data = {
                "group": self.get_type(),
                "klass": self.__class__.__name__,
                "receiver": self.format_receiver_for_notification_history(receiver),
                "details": self.get_notification_history_details(),
                "category": self.category,
            }

            if hasattr(self.item, "id"):
                if isinstance(self.item.id, int):
                    content_type = ContentType.objects.get_for_model(self.item)
                    data["content_type"] = content_type
                    data["object_id"] = self.item.id

            if getattr(settings, "UNIVERSAL_NOTIFICATIONS_HISTORY", True):
                if getattr(settings, "UNIVERSAL_NOTIFICATIONS_HISTORY_USE_DATABASE", True):
                    NotificationHistory.objects.create(**data)

                logger.info("Notification sent: {}".format(data))

    def send(self):
        self.check_category()
        self.verify_and_filter_receivers_subscriptions()
        prepared_receivers = self.prepare_receivers()
        prepared_message = self.prepare_message()
        result = self.send_inner(prepared_receivers, prepared_message)
        self.save_notifications(prepared_receivers)
        if self.chaining:
            for conf in self.chaining:
                args = [conf, self.item, self.receivers, self.context, result]
                if conf["delay"] > 0:
                    process_chained_notification.apply_async(args, countdown=conf["delay"])
                else:  # no delay, so execute function directly, not as task
                    process_chained_notification(*args)
        return result


class WSNotification(NotificationBase):
    message = None  # required
    serializer_class = None  # required, DRF serializer
    serializer_many = False
    check_subscription = False

    def prepare_receivers(self):
        return set(self.receivers)

    def prepare_message(self):
        return {
            "message": self.message,
            "data": self.serializer_class(self.item, context=self.get_context(), many=self.serializer_many).data
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
    send_async = getattr(settings, "UNIVERSAL_NOTIFICATIONS_SMS_SEND_IN_TASK", True)

    def prepare_receivers(self):
        """Filter out duplicated phone numbers"""
        receivers = set()
        phone_numbers = set()
        for r in self.receivers:
            if r.phone not in phone_numbers:
                receivers.add(r)

        return receivers

    def prepare_message(self):
        return Template(self.message).render(Context(self.get_context()))

    def send_inner(self, prepared_receivers, prepared_message):
        for receiver in prepared_receivers:
            self.context["receiver"] = receiver
            send_sms(receiver.phone, self.prepare_message(), send_async=self.send_async)

    def get_notification_history_details(self):
        return self.prepare_message()

    @classmethod
    def get_type(cls):
        return "SMS"


class EmailNotification(NotificationBase):
    """Email notification

    Attributes:
        email_name      required
        email_subject   if not provided, will try to extract "<title>" tag from email template
        sender          optional sender
        categories      optional categories which are added to EmailMessage (can be used with SendGrid)
        sendgrid_asm    SendGrid unsubscribe groups configuration, available properties:
                        * group_id - ID of an unsubscribe group
                        * groups_to_display - Unsubscribe groups to display
    """
    email_name = None  # required
    email_subject = None  # if not provided, will try to extract "<title>" tag from email template
    sender = None  # optional
    categories = []  # optional
    sendgrid_asm = {}
    use_premailer = None

    def __init__(self, item, receivers, context=None, attachments=None):
        self.attachments = attachments or []
        super(EmailNotification, self).__init__(item, receivers, context)

    @classmethod
    def format_receiver(cls, receiver):
        receiver_name = "%s %s" % (receiver.first_name, receiver.last_name)
        receiver_name = re.sub(r"\S*@\S*\s?", "", receiver_name).strip()
        return formataddr((receiver_name, receiver.email))

    def prepare_receivers(self):
        return set(self.receivers)

    def prepare_message(self):
        return self.get_context()

    def format_receiver_for_notification_history(self, receiver):
        return receiver.email

    def prepare_subject(self):
        if self.email_subject:
            return Template(self.email_subject).render(Context(self.get_context()))

    def get_notification_history_details(self):
        return self.email_name

    @classmethod
    def get_type(cls):
        return "Email"

    def get_full_template_context(self):
        is_secure = getattr(settings, "UNIVERSAL_NOTIFICATIONS_IS_SECURE", False)
        protocol = "https://" if is_secure else "http://"
        site = Site.objects.get_current()
        return {
            "site": site,
            "STATIC_URL": settings.STATIC_URL,
            "is_secure": is_secure,
            "protocol": protocol,
            "domain": site.domain
        }

    def get_template(self):
        return get_template("emails/email_%s.html" % self.email_name)

    def send_email(self, subject, context, receiver):
        template = self.get_template()
        html = template.render(context)
        # update paths
        base = context["protocol"] + context["domain"]
        sender = self.sender or settings.DEFAULT_FROM_EMAIL
        if getattr(settings, "UNIVERSAL_NOTIFICATIONS_USE_PREMAILER", True) and self.use_premailer is not False:
            html = html.replace("{settings.STATIC_URL}CACHE/".format(settings=settings),
                                "{settings.STATIC_ROOT}/CACHE/".format(settings=settings))  # get local file
            html = Premailer(html,
                             remove_classes=False,
                             exclude_pseudoclasses=False,
                             keep_style_tags=True,
                             include_star_selectors=True,
                             strip_important=False,
                             cssutils_logging_level=logging.CRITICAL,
                             base_url=base).transform()

        # if subject is not provided, try to extract it from <title> tag
        if not subject:
            self.email_subject = self.__get_title_from_html(html)
            subject = self.prepare_subject()

        email = EmailMessage(subject, html, sender, [receiver], attachments=self.attachments)
        if self.categories:
            email.categories = self.categories

        if self.sendgrid_asm:
            email.asm = self.sendgrid_asm

        email.content_subtype = "html"
        email.send(fail_silently=False)

    def send_inner(self, prepared_receivers, prepared_message):
        subject = self.email_subject
        if subject:
            subject = self.prepare_subject()

        context = self.get_full_template_context()
        context.update(prepared_message)
        for receiver in prepared_receivers:
            context["receiver"] = receiver
            self.send_email(subject, context, self.format_receiver(receiver))

    def __get_title_from_html(self, html):
        m = re.search(r"<title>(.*?)</title>", html, re.MULTILINE | re.IGNORECASE)
        if not m:
            raise ImproperlyConfigured("Email notification {} does not provide email_subject nor "
                                       "<title></title> in the template".format(self.email_name))

        return m.group(1)


class PushNotification(NotificationBase):
    title = None  # required, django template string
    description = ""  # optional, django template string

    @classmethod
    def get_type(cls):
        return "Push"

    def prepare_receivers(self):
        return set(self.receivers)

    def prepare_body(self):  # self.item & self.context can be used here
        return {}

    def prepare_message(self):
        context = Context(self.get_context())
        return {
            "title": Template(self.title).render(context),
            "description": Template(self.description).render(context),
            "data": self.prepare_body()
        }

    def format_receiver_for_notification_history(self, receiver):
        return receiver.email

    def send_inner(self, prepared_receivers, prepared_message):  # TODO
        for receiver in prepared_receivers:
            for d in Device.objects.filter(user=receiver, is_active=True):
                d.send_message(prepared_message["title"], prepared_message["description"], **prepared_message["data"])

    def get_notification_history_details(self):
        return self.prepare_message()
