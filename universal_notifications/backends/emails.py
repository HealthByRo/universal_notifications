# -*- coding: utf-8 -*-
from django.conf import settings
from django.contrib.sites.models import Site
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from premailer import Premailer


def send_email(template, to, subject, variables={}, fail_silently=False, cms=False, replace_variables={}, sender=None):
    variables['site'] = Site.objects.get_current()
    variables['STATIC_URL'] = settings.STATIC_URL
    variables['is_secure'] = getattr(settings, 'UNIVERSAL_NOTIFICATIONS_IS_SECURE', False)
    html = render_to_string('emails/email_%s.html' % template, variables)
    protocol = 'https://' if variables['is_secure'] else 'http://'
    replace_variables['protocol'] = protocol
    domain = variables['site'].domain
    replace_variables['domain'] = domain
    for key, value in replace_variables.items():
        if not value:
            value = ''
        html = html.replace('{%s}' % key.upper(), value)
    # Update path to have domains
    base = protocol + domain
    if sender is None:
        sender = settings.DEFAULT_FROM_EMAIL
    html = Premailer(html,
                     remove_classes=False,
                     exclude_pseudoclasses=False,
                     keep_style_tags=True,
                     include_star_selectors=True,
                     strip_important=False,
                     base_url=base).transform()
    email = EmailMessage(subject, html, sender, [to])
    email.content_subtype = "html"
    email.send(fail_silently=fail_silently)
