# -*- coding: utf-8 -*-

from django.utils import timezone

from enrich.data import managers
from enrich.models import BingAPILookup

from .models import UserGrammarRule, UserWord


def rule_hsk_level(rule):
    if not rule.hsk_id or rule.hsk_id == "other":
        return 0

    return int(rule.hsk_id[0:1])


def update_user_words(voc, user):
    from_lang = "zh-Hans"
    to_lang = "en"

    words = (
        BingAPILookup.objects.filter(source_text__in=voc.keys(), from_lang=from_lang, to_lang=to_lang)
        .values_list("id", "source_text")
        .order_by("id")
    )

    # FIXME: TODO: think of a better way to do this in bulk
    # currently there are duplicates in BingAPILookup so can't do better
    word_ids = [w[0] for w in words]
    # print('word_ids', word_ids)
    words_w_ids = {}
    for w in words:
        if w[1] not in words_w_ids:
            words_w_ids[w[1]] = w[0]

    # print('words_w_ids', words_w_ids)
    uws = UserWord.objects.filter(user=user, word_id__in=word_ids)
    # print('uws', uws)
    new_words = []
    dedup_words = set()

    # update existing
    for uw in uws:
        if uw.word.source_text not in dedup_words:
            dedup_words.add(uw.word.source_text)  # dedups both duplicates in the queryset and finds updates
            # print('updating', uw.word.source_text)
            uw.nb_seen += voc[uw.word.source_text][0]
            uw.last_seen = timezone.now()
            if voc[uw.word.source_text][1] > 0:
                uw.nb_seen_since_last_check = 0
                uw.nb_checked += voc[uw.word.source_text][1]
                uw.last_checked = timezone.now()
            else:
                uw.nb_seen_since_last_check += voc[uw.word.source_text][0]

            uw.save()
            # print(f'would save {uw}')
    # print('dedup words', dedup_words)
    # insert new
    for k, val in voc.items():
        if k not in dedup_words and k in words_w_ids:
            new_words.append(
                UserWord(
                    user=user,
                    word_id=words_w_ids[k],
                    nb_seen=val[0],
                    # last_seen=timezone.now(),
                    nb_seen_since_last_check=(0 if val[1] else val[0]),
                    nb_checked=val[1],
                )
            )

    # print('created new user words', new_words)
    return UserWord.objects.bulk_create(new_words)


def update_user_rules(rlz, user):
    if len(rlz.keys()) == 0:
        # print('no rules for this text')
        return None

    dedup_rules = set()
    # print('rlz keys', rlz.keys())

    ugrs = UserGrammarRule.objects.filter(user=user, grammar_rule_id__in=rlz.keys())
    # print('ugrs', ugrs)
    for ugr in ugrs:
        dedup_rules.add(str(ugr.grammar_rule.id))  # dedups both duplicates in the queryset and finds updates
        ugr.nb_seen += rlz[str(ugr.grammar_rule.id)][0]
        ugr.last_seen = timezone.now()
        if rlz[str(ugr.grammar_rule.id)][1] > 0:
            ugr.nb_checked += rlz[str(ugr.grammar_rule.id)][1]
            ugr.nb_seen_since_last_check = 0
            ugr.last_checked = timezone.now()
        if rlz[str(ugr.grammar_rule.id)][2] > 0:
            ugr.nb_studied += rlz[str(ugr.grammar_rule.id)][2]
            ugr.nb_seen_since_last_study = 0
            ugr.last_studied = timezone.now()
        ugr.save()

    new_user_rules = []
    for k, val in rlz.items():
        if k not in dedup_rules:
            new_user_rules.append(
                UserGrammarRule(
                    user=user,
                    grammar_rule_id=int(k),
                    nb_seen=val[0],
                    nb_checked=val[1],
                    nb_studied=val[2],
                    last_checked=(timezone.now() if val[1] else None),
                    last_studied=(timezone.now() if val[2] else None),
                    nb_seen_since_last_check=(0 if val[1] else 1),
                    nb_seen_since_last_study=(0 if val[2] else 1),
                )
            )

    # print('create new user rules', new_user_rules)
    return UserGrammarRule.objects.bulk_create(new_user_rules)


def add_lemmas(model):
    for s in model["sentences"]:
        for t in s["tokens"]:
            t["lemma"] = t["word"]


def vocab_levels(vocab):
    lang_pair = "zh-Hans:en"  # get_username_lang_pair(request)
    manager = managers.get(lang_pair)
    hsk = None
    for m in manager.metadata():
        if m.name() == "hsk":
            hsk = m

    if not hsk:
        raise Exception("Can not find HSK")

    levels = {}
    dedup = set()
    for k in vocab.keys():
        # print(hsk.meta_for_word(k))
        ls = hsk.meta_for_word(k)
        if ls and k not in dedup:
            if not ls[0]["hsk"] in levels:
                levels[ls[0]["hsk"]] = []
            levels[ls[0]["hsk"]].append(k)
            dedup.add(k)
    return levels
