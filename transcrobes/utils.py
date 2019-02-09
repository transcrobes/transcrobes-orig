# -*- coding: utf-8 -*-

import base64
import json
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView


def get_username_lang_pair(request):
    auth_header = request.META.get('HTTP_AUTHORIZATION')
    scheme, token = auth_header.split(' ')
    if scheme == 'Bearer':
        encoded_payload = token.split('.')[1]  # isolates payload
        encoded_payload += "=" * ((4 - len(encoded_payload) % 4) % 4) # properly pad
        payload = json.loads(base64.b64decode(encoded_payload).decode("utf-8"))
        return payload['username'], payload['lang_pair']
    else:
        # it must be basic, meaning we have already auth'ed with the DB
        return request.user.username, request.user.transcrober.lang_pair()

class TranscrobesTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super(TranscrobesTokenObtainPairSerializer, cls).get_token(user)

        token['username'] = user.username
        token['lang_pair'] = user.transcrober.lang_pair()

        return token

class TranscrobesTokenObtainPairView(TokenObtainPairView):
    serializer_class = TranscrobesTokenObtainPairSerializer
