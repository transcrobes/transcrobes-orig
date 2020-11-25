# -*- coding: utf-8 -*-
import base64
import json

from django.contrib.auth.models import User
from rest_framework_simplejwt.backends import TokenBackend
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer, TokenRefreshSerializer
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView


def default_definition(manager, w):
    t = {"word": w, "pos": "NN", "lemma": w}  # fake pos, here we don't care
    note_defs = note_format(manager.default().get_standardised_defs(t), w)
    if not note_defs:
        for x in manager.secondary():
            note_defs = note_format(x.get_standardised_defs(t), w)
            if note_defs:
                break

        if not note_defs:
            note_defs = note_format(manager.default().get_standardised_fallback_defs(t), w)
    return note_defs[0]  # the fallback *always* has at least (exactly?) one


def note_format(std_format, chars):
    """
    This method, with unfortunately named variables...
    Basically groups the definitions by POS, so that when the client
    gets the json it can present the definitions grouped by POS.

    The idea is that it is unlikely that there will be lots of homographs
    that have the same POS and a different pronunciation, at least in Chinese

    When the pronunciation is different, two (or more) pseudo-notes (that can be added
    to the user DB) are created. The user is then presented with an option to add ONE
    of the options.
    Currently there is support for adding multiple notes with the same characters in
    about half the system. The rest will eventually need to be added, but the extra
    effort at this stage for little gain is too much to warrant it at the moment.
    """
    # TODO: The above will need to be validated!
    by_py = {}
    for pos, defs in std_format.items():
        for defie in defs:
            if not defie["pinyin"] in by_py:
                by_py[defie["pinyin"]] = {}
            if not defie["opos"] in by_py[defie["pinyin"]]:
                by_py[defie["pinyin"]][defie["opos"]] = []
            by_py[defie["pinyin"]][defie["opos"]].append(defie)

    json_notes = []
    for py, defs in by_py.items():
        json_note = {
            "Simplified": chars,
            "Pinyin": py,
        }
        ds = []
        for pos, defies in defs.items():
            ds.append("{} {}".format(pos, ", ".join(d["normalizedTarget"] for d in defies)))

        json_note["Meaning"] = "; ".join(ds)
        json_notes.append(json_note)
    return json_notes


def get_username_lang_pair(request):
    auth_header = request.META.get("HTTP_AUTHORIZATION")
    scheme, token = auth_header.split(" ") if auth_header else "", ""
    if scheme == "Bearer":
        encoded_payload = token.split(".")[1]  # isolates payload
        encoded_payload += "=" * ((4 - len(encoded_payload) % 4) % 4)  # properly pad
        payload = json.loads(base64.b64decode(encoded_payload).decode("utf-8"))
        return payload["username"], payload["lang_pair"]

    # it must be basic, meaning we have already auth'ed with the DB
    return request.user.username, request.user.transcrober.lang_pair()


class TranscrobesTokenObtainPairSerializer(TokenObtainPairSerializer):  # pylint: disable=W0223
    @classmethod
    def get_token(cls, user):
        token = super(TranscrobesTokenObtainPairSerializer, cls).get_token(user)

        token["username"] = user.username
        token["lang_pair"] = user.transcrober.lang_pair()

        # FIXME: this is a nasty hack that should be replaced with something well architected
        # this will refresh the materialised view "user_vocabulary", so that getting the notes
        # in the API will be up-to-date
        user.transcrober.refresh_vocabulary()

        return token


class TranscrobesTokenObtainPairView(TokenObtainPairView):
    serializer_class = TranscrobesTokenObtainPairSerializer


# FIXME: actually, we should probably just not use the refresh token and force
# a proper reauth token for every expiration. Alas, the Chrome extension updates are
# a huge pain, so nasty hack here for the moment
class TranscrobesTokenRefreshSerializer(TokenRefreshSerializer):  # pylint: disable=W0223
    def validate(self, attrs):
        data = super().validate(attrs)

        # FIXME: Are we Ok not verifying here?
        valid_data = TokenBackend(algorithm="HS256").decode(data["access"], verify=False)
        User.objects.get(id=valid_data["user_id"]).transcrober.refresh_vocabulary()

        return data


class TranscrobesTokenRefreshView(TokenRefreshView):
    serializer_class = TranscrobesTokenRefreshSerializer
