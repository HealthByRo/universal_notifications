import logging

from django.conf import settings
from django.contrib.sites.models import Site
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from premailer import Premailer


def send_email(template, to, subject, variables=None, fail_silently=False, cms=False, replace_variables=None,
               sender=None, attachments=None, categories=None):
    attachments = attachments or []
    if variables is None:
        variables = {}
    if replace_variables is None:
        replace_variables = {}
    variables["site"] = Site.objects.get_current()
    variables["STATIC_URL"] = settings.STATIC_URL
    variables["is_secure"] = getattr(settings, "UNIVERSAL_NOTIFICATIONS_IS_SECURE", False)
    protocol = "https://" if variables["is_secure"] else "http://"
    variables["protocol"] = protocol
    replace_variables['protocol'] = protocol
    domain = variables["site"].domain
    variables["domain"] = domain
    replace_variables["domain"] = domain
    html = render_to_string('emails/email_%s.html' % template, variables)
    for key, value in replace_variables.items():
        if not value:
            value = ""
        html = html.replace("{%s}" % key.upper(), value)
    # Update path to have domains
    base = protocol + domain
    if sender is None:
        sender = settings.DEFAULT_FROM_EMAIL
    if getattr(settings, "UNIVERSAL_NOTIFICATIONS_USE_PREMAILER", True):
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
    email = EmailMessage(subject, html, sender, [to], attachments=attachments)
    if categories:
        email.categories = categories
    email.content_subtype = "html"
    email.send(fail_silently=fail_silently)
