# -*- coding: utf-8 -*-
import base64
import json
import zlib

from django.core import exceptions
from django.db import models
from django.forms import fields
from django.forms.utils import ValidationError as FormValidationError
from django.utils.translation import ugettext_lazy as _
from six import string_types


class JSONField(models.TextField):
    """JSONField is a generic textfield that neatly serializes/unserializes JSON objects seamlessly."""

    # Minimum length of value before compression kicks in
    compression_threshold = 64

    def __init__(self, verbose_name=None, json_type=None, compress=False, *args, **kwargs):
        self.json_type = json_type
        self.compress = compress
        super(JSONField, self).__init__(verbose_name, *args, **kwargs)

    def from_db_value(self, value, expression, connection, context):
        return self.to_python(value)

    def to_python(self, value):
        """Convert our string value to JSON after we load it from the DB."""
        if isinstance(value, string_types):
            if self.compress and value.startswith('zlib;;'):
                value = zlib.decompress(base64.decodestring(value[6:]))

            try:
                value = json.loads(value)
            except ValueError:
                pass

        if self.json_type and not isinstance(value, self.json_type):
            raise exceptions.ValidationError(
                "%r is not of type %s (error occured when trying to access "
                "'%s.%s' field)" %
                (value, self.json_type, self.model._meta.db_table, self.name))
        return value

    def get_db_prep_save(self, value, connection):
        """Convert our JSON object to a string before we save."""
        if self.json_type and not isinstance(value, self.json_type):
            raise TypeError("%r is not of type %s" % (value, self.json_type))

        try:
            value = json.dumps(value)
        except TypeError, e:
            raise ValueError(e)

        if self.compress and len(value) >= self.compression_threshold:
            value = 'zlib;;' + base64.encodestring(zlib.compress(value))

        return super(JSONField, self).get_db_prep_save(value, connection=connection)

    def value_to_string(self, obj):
        value = self._get_val_from_obj(obj)
        return value

    def formfield(self, **kwargs):
        defaults = {'form_class': JSONFormField}
        defaults.update(kwargs)
        return super(JSONField, self).formfield(**defaults)


class JSONFormField(fields.CharField):

    def clean(self, value):

        if not value and not self.required:
            return None

        value = super(JSONFormField, self).clean(value)

        if isinstance(value, string_types):
            try:
                json.loads(value)
            except ValueError:
                raise FormValidationError(_("Enter valid JSON"))
        return value
