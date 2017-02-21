import re

import phonenumbers
from django.conf import settings
from twilio.rest import TwilioLookupsClient, TwilioRestClient

try:
    # Wide UCS-4 build
    emoji_pattern = re.compile(u'['
                               u'\U0001F300-\U0001F64F'
                               u'\U0001F680-\U0001F6FF'
                               u'\u2600-\u26FF\u2700-\u27BF]+',
                               re.UNICODE)
except re.error:
    # Narrow UCS-2 build
    emoji_pattern = re.compile(u'('
                               u'\ud83c[\udf00-\udfff]|'
                               u'\ud83d[\udc00-\ude4f\ude80-\udeff]|'
                               u'[\u2600-\u26FF\u2700-\u27BF])+',
                               re.UNICODE)


def get_twilio_client(lookups=False):
    if lookups:
        return TwilioLookupsClient(settings.UNIVERSAL_NOTIFICATIONS_TWILIO_ACCOUNT,
                                   settings.UNIVERSAL_NOTIFICATIONS_TWILIO_TOKEN)
    return TwilioRestClient(settings.UNIVERSAL_NOTIFICATIONS_TWILIO_ACCOUNT,
                            settings.UNIVERSAL_NOTIFICATIONS_TWILIO_TOKEN)


def format_phone(phone):
    if not phone:
        return ''
    region = 'US'
    if phone.startswith('+'):
        region = None
    parsed = phonenumbers.parse(phone, region)
    return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)


def clean_text(text):
    return emoji_pattern.sub(r'', text)


def validate_mobile(value):
    """Validate if number is mobile

    Lookup Twilio info about number and validate if carrier is mobile or voip

    Arguments:
        value {string|phonenumbers.PhoneNumber} -- phone number

    Returns:
        bool -- return True if number is mobile
    """
    if not settings.UNIVERSAL_NOTIFICATIONS_VALIDATE_MOBILE:
        return True

    if not isinstance(value, phonenumbers.PhoneNumber):
        try:
            value = phonenumbers.parse(value, 'US')
        except phonenumbers.phonenumberutil.NumberParseException:
            return False

    number = phonenumbers.format_number(value, phonenumbers.PhoneNumberFormat.E164)
    client = get_twilio_client(lookups=True)
    response = client.phone_numbers.get(number, include_carrier_info=True)
    if response.carrier['type'] not in ['voip', 'mobile']:
        return False
    return True
