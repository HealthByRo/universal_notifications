# -*- coding: utf-8 -*-
from importlib import import_module

from django.apps import apps
from django.template import TemplateDoesNotExist, TemplateSyntaxError
from django.utils.safestring import mark_safe
from rest_framework.compat import coreapi
from universal_notifications.notifications import (EmailNotification, NotificationBase, PushNotification,
                                                   SMSNotification, WSNotification)

BASE_NOTIFICATIONS = (EmailNotification, NotificationBase, PushNotification, SMSNotification, WSNotification)


class BaseGenerator(object):
    def __init__(self, obj, *args, **kwargs):
        super(BaseGenerator, self).__init__(*args, **kwargs)
        self._obj = obj

    def get_summary(self):
        return "TODO: summary"

    def get_type(self):
        return "TODO: type"

    def get_notes(self):
        parts = [self.get_summary() + "\n", self._obj.__doc__]
        if self._obj.check_subscription:
            parts.append("<b>Subscription Category:</b> %s" % self._obj.category)
        parts.append(self.get_class_specific_notes())
        return "<br/><br/>".join(part for part in parts if part and part.strip())  # display only non empty parts

    def get_class_specific_notes(self):
        return "TODO: notes"

    def get_serializer(self):
        return None

    def skip(self):
        return False


class WSDocGenerator(BaseGenerator):
    def get_summary(self):
        return self._obj.message

    def get_type(self):
        return self.get_serializer().__name__

    def get_class_specific_notes(self):
        data = self.get_serializer().__name__
        if self._obj.serializer_many:
            data = "[%s*]" % data
        return "<b>Message</b><br/>%s<br/><br/><b>Data</b><br/>%s" % (self._obj.message, data)

    def get_serializer(self):
        if self._obj.serializer_class is None:
            # handling scase when serializer_class is defined during __init__
            return self._obj().serializer_class
        return self._obj.serializer_class

    def skip(self):
        return not self._obj.message


class SMSDocGenerator(BaseGenerator):
    def get_summary(self):
        return "SMS"

    def get_type(self):
        return None

    def get_class_specific_notes(self):
        return "<b>Template:</b><br/>%s" % self._obj.message

    def skip(self):
        return not self._obj.message


class EmailDocGenerator(BaseGenerator):
    template_loader = None

    # ++ THIS IS UGLY. TODO: Find better method
    @classmethod
    def get_template_loader(cls):
        if not cls.template_loader:
            from django.template.loaders.filesystem import Loader
            from django.template.engine import Engine

            default_template_engine = Engine.get_default()
            cls.template_loader = Loader(default_template_engine)
        return cls.template_loader

    @classmethod
    def get_template(cls, template_name):
        template_loader = cls.get_template_loader()
        try:
            source, dummy = template_loader.load_template_source(template_name)
            return source
        except (TemplateDoesNotExist, TemplateSyntaxError):
            return ""
    # --

    def get_summary(self):
        return self._obj.email_name

    def get_type(self):
        return None

    def get_class_specific_notes(self):
        notes = "<b>Subject:</b><br/>%s<br/><br/><b>Preview:</b><br/>%s" % (
            self._obj.email_subject,
            self.get_template("emails/email_%s.html" % self._obj.email_name)
        )
        return mark_safe(notes)

    def skip(self):
        return not self._obj.email_name


class NotificationsDocs(object):
    _registry = {}
    _autodiscovered = False
    _serializers = set()
    _generator_mapping = {
        EmailNotification: EmailDocGenerator,
        SMSNotification: SMSDocGenerator,
        WSNotification: WSDocGenerator
    }

    @classmethod
    def autodiscover(cls):
        if cls._autodiscovered:
            return

        cls._autodiscovered = True

        # classes
        for app_config in apps.get_app_configs():
            if app_config.name == "universal_notifications":  # no self importing
                continue
            try:
                module = import_module("%s.%s" % (app_config.name, "notifications"))
                for key in dir(module):
                    item = getattr(module, key)
                    if issubclass(item, NotificationBase) and item not in BASE_NOTIFICATIONS:
                        notification_type = item.get_type()
                        if notification_type not in cls._registry:
                            cls._registry[notification_type] = {}
                        item_key = "%s.%s" % (key, app_config.name)
                        item_path = "%s (%s.notifications)" % (key, app_config.name)

                        generator = cls.get_generator(item)
                        if not generator.skip():
                            serializer = generator.get_serializer()
                            if serializer:
                                cls._serializers.add(serializer)
                            cls._registry[notification_type][item_key] = {"cls": item, "path": item_path}
            except Exception:
                pass

    @classmethod
    def get_types(cls):
        return sorted(cls._registry.keys())

    @classmethod
    def get_notifications(cls, notification_type):
        return sorted(cls._registry.get(notification_type, {}).items(), key=lambda x: x[0])

    @classmethod
    def get_generator(cls, notification_cls):
        for key_cls, generator_cls in cls._generator_mapping.items():
            if issubclass(notification_cls, key_cls):
                return generator_cls(notification_cls)
        return BaseGenerator(notification_cls)

    @classmethod
    def generate_notifications_docs(cls, notification_type):
        links = {}
        for key, value in cls.get_notifications(notification_type):
            generator = cls.get_generator(value["cls"])
            links[value["path"]] = coreapi.Link(
                title=key,
                description=generator.get_notes(),
                action="GET",
                url=value["path"]
            )

        return links
