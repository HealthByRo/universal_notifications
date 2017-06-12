import boto3
from django.conf import settings
from universal_notifications.backends.sms.abstract import SMSEngineAbtract
from universal_notifications.models import PhoneSent


def get_sns_client(lookups=False):
    return boto3.client(
        'sns',
        aws_access_key_id=getattr(settings, 'AWS_ACCESS_KEY_ID', ''),
        aws_secret_access_key=getattr(settings, 'AWS_SECRET_ACCESS_KEY', ''),
        region_name=getattr(settings, 'AWS_DEFAULT_REGION', 'us-east-1'),
    )


class Engine(SMSEngineAbtract):

    def send(self, obj):
        if not getattr(settings, 'UNIVERSAL_NOTIFICATIONS_AMAZON_SNS_API_ENABLED', False):
            self.status = PhoneSent.STATUS_SENT
            return

        if not obj.sms_id:
            try:
                sns_client = get_sns_client()
                response = sns_client.publish(
                    PhoneNumber=obj.receiver.number,
                    Message=obj.text,
                )
                obj.status = PhoneSent.STATUS_SENT
                obj.sms_id = response['MessageId']

            except Exception as e:
                obj.error_message = e
                obj.status = PhoneSent.STATUS_FAILED
