# -*- coding: utf-8 -*-

from rest_framework_simplejwt.serializers import TokenObtainPairSerializer, TokenRefreshSerializer
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView


class TranscrobesTokenObtainPairSerializer(TokenObtainPairSerializer):  # pylint: disable=W0223
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["username"] = user.username
        token["user_id"] = user.id
        token["lang_pair"] = user.transcrober.lang_pair()
        token["provs"] = user.transcrober.dictionary_ordering.split(",")
        return token


class TranscrobesTokenObtainPairView(TokenObtainPairView):
    serializer_class = TranscrobesTokenObtainPairSerializer


class TranscrobesTokenRefreshSerializer(TokenRefreshSerializer):  # pylint: disable=W0223
    def validate(self, attrs):
        data = super().validate(attrs)

        # FIXME: Are we Ok not verifying here?
        # valid_data = TokenBackend(algorithm="HS256").decode(data["access"], verify=False)
        # User.objects.get(id=valid_data["user_id"]).transcrober.refresh_vocabulary()

        return data


class TranscrobesTokenRefreshView(TokenRefreshView):
    serializer_class = TranscrobesTokenRefreshSerializer
