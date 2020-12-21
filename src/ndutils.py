# -*- coding: utf-8 -*-
import asyncio
import base64
import json
import re


# FIXME: replace with https://github.com/tsroten/hanzidentifier or https://github.com/tsroten/zhon
# FIXME: move somewhere more appropriate, like ndutils
def to_enrich(word):
    return bool(re.search(".*[\u4e00-\u9fff]+.*", word))


def lemma(token):
    return token.get("l") or token["lemma"]


def phone_rep(token):
    return token.get("p") or token["pinyin"]


def user_imports_path(instance, filename):
    # WARNING! Only useful in a modiles.FileField
    # file uploads for imports will be uploaded to MEDIA_ROOT/user_<id>/imports/<filename>
    return f"user_{instance.user.id}/imports/{filename}"


def user_resources_path(user, filename):
    return f"user_{user.id}/resources/{filename}"


def do_response(response):
    response["Access-Control-Allow-Origin"] = "*"
    response["Access-Control-Allow-Methods"] = "POST, OPTIONS"
    response["Access-Control-Allow-Headers"] = "X-Requested-With, Content-Type, Authorization"
    return response


def clean_definitions(definitions):
    for k in definitions.keys():
        for definition in definitions[k]:
            clean_standardised(definition)
    return definitions


def clean_standardised(definition):
    definition["nt"] = definition["normalizedTarget"]
    definition["cf"] = definition["confidence"]
    # definition["p"] = definition["pinyin"]
    for key in ["confidence", "opos", "pinyin", "normalizedTarget", "trans_provider"]:
        try:
            del definition[key]
        except KeyError:
            pass
    return definition


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


async def gather_with_concurrency(n, *tasks):
    semaphore = asyncio.Semaphore(n)

    async def sem_task(task):
        async with semaphore:
            return await task

    return await asyncio.gather(*(sem_task(task) for task in tasks))


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
    # FIXME: Now only used in obsolete testing api, can be deleted
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
            if not phone_rep(defie) in by_py:
                by_py[phone_rep(defie)] = {}
            if not defie["opos"] in by_py[phone_rep(defie)]:
                by_py[phone_rep(defie)][defie["opos"]] = []
            by_py[phone_rep(defie)][defie["opos"]].append(defie)

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
