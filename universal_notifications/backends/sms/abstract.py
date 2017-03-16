import phonenumbers
from django.conf import settings


class SMSEngineAbtract(object):

    def get_service_number(self):
        return ''

    def add_to_queue(self, obj):
        self.send(obj.message)
        obj.message.save()

    def send(self, obj, **kwargs):
        raise NotImplementedError

    def parse_received(self, raw):
        raise NotImplementedError

    def validate_mobile(self, value):
        """Validate if number is mobile

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
        return value
