# -*- coding: utf-8 -*-
import logging

import cssutils
from django.conf import settings
from django.contrib.sites.models import Site
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from premailer import Premailer

try:
    from django.utils.importlib import import_module
except ImportError:
    from importlib import import_module

cssutils.log.setLevel(logging.CRITICAL)

if hasattr(settings, "UNSUBSCRIBE_MODEL"):
    __path, __symbol = getattr(settings, 'UNSUBSCRIBE_MODEL').rsplit('.', 1)
    UnsubscribedModel = getattr(import_module(__path), __symbol)
else:
    UnsubscribedModel = None


def send_email(template, to, subject, variables={}, fail_silently=False, cms=False, replace_variables={}):
    variables['site'] = Site.objects.get_current()
    variables['STATIC_URL'] = settings.STATIC_URL
    variables['is_secure'] = getattr(settings, 'IS_SECURE', False)
    html = render_to_string('emails/email_%s.html' % template, variables)
    protocol = 'https://' if variables['is_secure'] else 'http://'
    replace_variables['protocol'] = protocol
    domain = variables['site'].domain
    replace_variables['domain'] = domain
    for key, value in replace_variables.iteritems():
        if not value:
            value = ''
        html = html.replace('{%s}' % key.upper(), value)
    # Update path to have domains
    base = protocol + domain
    html = Premailer(html,
                     remove_classes=False,
                     exclude_pseudoclasses=False,
                     keep_style_tags=True,
                     include_star_selectors=True,
                     strip_important=False,
                     base_url=base).transform()
    email = EmailMessage(subject, html, settings.DEFAULT_FROM_EMAIL, [to])
    email.content_subtype = "html"
    email.send(fail_silently=fail_silently)
