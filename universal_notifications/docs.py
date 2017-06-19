# -*- coding: utf-8 -*-
import json
from importlib import import_module

import rest_framework_swagger as rfs
from django.apps import apps
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.utils import six
from django.utils.safestring import mark_safe
from django.views.generic import View
from rest_framework.settings import api_settings
from rest_framework.views import Response
from rest_framework_swagger.apidocview import APIDocView
from rest_framework_swagger.compat import OrderedDict, import_string
from rest_framework_swagger.docgenerator import DocumentationGenerator
from rest_framework_swagger.introspectors import IntrospectorHelper
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
        parts = [self._obj.__doc__]
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
        return self._obj.serializer_class.__name__

    def get_class_specific_notes(self):
        data = self._obj.serializer_class.__name__
        if self._obj.serializer_many:
            data = "[%s*]" % data
        return "<b>Message</b><br/>%s<br/><br/><b>Data</b><br/>%s" % (self._obj.message, data)

    def get_serializer(self):
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
        except:
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


class PatchedDocumentationGenerator(DocumentationGenerator):
    def __init__(self, *args, **kwargs):
        pass  # ignore init from oryginal documentation generator


class NotificationsDocs(object):
    _registry = {}
    _autodiscovered = False
    _serializers = set()
    _generator_mapping = {
        EmailNotification: EmailDocGenerator,
        SMSNotification: SMSDocGenerator,
        WSNotification: WSDocGenerator
    }
    _pdg = PatchedDocumentationGenerator()

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
            except:
                pass

        # serializers
        cls._serializers.update(cls._pdg._find_field_serializers(cls._serializers))

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
        notifications_docs = []
        for key, value in cls.get_notifications(notification_type):
            generator = cls.get_generator(value["cls"])
            notifications_docs.append({
                "operations": [{
                    "parameters": [],
                    "nickname": key,
                    "notes": generator.get_notes(),
                    "summary": generator.get_summary(),
                    "type": generator.get_type(),
                    "method": "GET"
                }],
                "path": value["path"],
                "description": ""
            })

        return notifications_docs

    # ++ CODE TAKEN FROM DJANGO REST SWAGGER & MODIFIED

    @classmethod
    def generate_models_docs(cls):
        models_docs = {}

        for serializer in cls._serializers:
            data = cls._pdg._get_serializer_fields(serializer)

            serializer_name = IntrospectorHelper.get_serializer_name(serializer)
            r_name = serializer_name
            r_properties = OrderedDict((k, v) for k, v in data["fields"].items() if k not in data["write_only"])
            models_docs[r_name] = {
                "id": r_name,
                "required": [i for i in r_properties.keys()],
                "properties": r_properties,
            }

        return models_docs
    # -- CODE TAKEN FROM DJANGO REST SWAGGER & MODIFIED


# ++ CODE TAKEN FROM DJANGO REST SWAGGER & MODIFIED

try:
    JSONRenderer = list(filter(
        lambda item: item.format == "json",
        api_settings.DEFAULT_RENDERER_CLASSES,
    ))[0]
except IndexError:
    from rest_framework.renderers import JSONRenderer


def get_full_base_path(request):
    try:
        base_path = rfs.SWAGGER_SETTINGS["base_path"]
    except KeyError:
        return request.build_absolute_uri(request.path).rstrip("/")
    else:
        protocol = "https" if request.is_secure() else "http"
        return "{0}://{1}".format(protocol, base_path.rstrip("/"))


class UniversalNotificationsUIView(View):
    def get(self, request, *args, **kwargs):
        if not self.has_permission(request):
            return self.handle_permission_denied(request)

        template_name = rfs.SWAGGER_SETTINGS.get("template_path")
        data = {
            "swagger_settings": {
                "discovery_url": "%s/api-docs/" % get_full_base_path(request),
                "api_key": rfs.SWAGGER_SETTINGS.get("api_key", ""),
                "api_version": rfs.SWAGGER_SETTINGS.get("api_version", ""),
                "token_type": rfs.SWAGGER_SETTINGS.get("token_type"),
                "enabled_methods": [],
                "doc_expansion": rfs.SWAGGER_SETTINGS.get("doc_expansion", ""),
            },
            "django_settings": {
                "CSRF_COOKIE_NAME": mark_safe(
                    json.dumps(getattr(settings, "CSRF_COOKIE_NAME", "csrftoken"))),
            }
        }
        try:
            return render_to_response(template_name, RequestContext(request, data))
        except TypeError:
            # fix for a bug in django 1.11
            return render_to_response(template_name, data)

    def has_permission(self, request):
        if rfs.SWAGGER_SETTINGS.get("is_superuser") and not request.user.is_superuser:
            return False

        if rfs.SWAGGER_SETTINGS.get("is_authenticated") and not request.user.is_authenticated():
            return False

        return True

    def handle_permission_denied(self, request):
        permission_denied_handler = rfs.SWAGGER_SETTINGS.get("permission_denied_handler")
        if isinstance(permission_denied_handler, six.string_types):
            permission_denied_handler = import_string(permission_denied_handler)

        if permission_denied_handler:
            return permission_denied_handler(request)
        else:
            raise PermissionDenied()


class UniversalNotificationsResourcesView(APIDocView):
    renderer_classes = (JSONRenderer, )

    def get(self, request, *args, **kwargs):
        apis = [{"path": "/" + path} for path in self.get_resources()]
        return Response({
            "apiVersion": rfs.SWAGGER_SETTINGS.get("api_version", ""),
            "swaggerVersion": "1.2",
            "basePath": self.get_base_path(),
            "apis": apis,
            "info": rfs.SWAGGER_SETTINGS.get("info", {
                "contact": "",
                "description": "",
                "license": "",
                "licenseUrl": "",
                "termsOfServiceUrl": "",
                "title": "",
            }),
        })

    def get_base_path(self):
        try:
            base_path = rfs.SWAGGER_SETTINGS["base_path"]
        except KeyError:
            return self.request.build_absolute_uri(
                self.request.path).rstrip("/")
        else:
            protocol = "https" if self.request.is_secure() else "http"
            return "{0}://{1}/{2}".format(protocol, base_path, "api-docs")

    def get_resources(self):
        return NotificationsDocs.get_types()


class UniversalNotificationsApiView(APIDocView):
    renderer_classes = (JSONRenderer, )

    def get(self, request, path, *args, **kwargs):
        result = Response({
            "apiVersion": rfs.SWAGGER_SETTINGS.get("api_version", ""),
            "swaggerVersion": "1.2",
            "basePath": self.api_full_uri.rstrip("/"),
            "resourcePath": "/" + path,
            "apis": NotificationsDocs.generate_notifications_docs(path),
            "models": NotificationsDocs.generate_models_docs(),
        })

        return result
# -- CODE TAKEN FROM DJANGO REST SWAGGER & MODIFIED
