# -*- coding: utf-8 -*-
from django.conf import settings
from django.http import QueryDict
from django.utils.safestring import SafeString
from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import AllowAny
from rest_framework.renderers import StaticHTMLRenderer
from rest_framework.response import Response
from rest_framework.serializers import Serializer
from universal_notifications.backends.sms.utils import clean_text
from universal_notifications.models import PhoneReceivedRaw


class TwilioAPI(GenericAPIView):
    """
    Receive SMS/Phone from Twilio
    """
    serializer_class = Serializer
    permission_classes = (AllowAny,)
    renderer_classes = (StaticHTMLRenderer,)

    def post(self, request):
        data = request.data

        # Clean emoji for now
        if isinstance(data, dict) and data.get('Body'):
            if isinstance(data, QueryDict):
                data = data.dict()
            data['Body'] = clean_text(data['Body'])
        PhoneReceivedRaw.objects.create(data=data)

        if data.get('Direction') == 'inbound':
            if data.get('CallStatus') == 'ringing':  # incoming voice call
                text = getattr(settings, 'UNIVERSAL_NOTIFICATIONS_TWILIO_CALL_RESPONSE_DEFAULT',
                               '<?xml version="1.0" encoding="UTF-8"?>' +
                               '<Response>' +
                               '<Say>Hello, thanks for calling. ' +
                               'To leave a message wait for the tone.</Say>' +
                               '<Record timeout="30" />'
                               '</Response>')
                return Response(SafeString(text), content_type='text/xml')
        return Response({}, status=status.HTTP_202_ACCEPTED)
