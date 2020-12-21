# -*- coding: utf-8 -*-

from __future__ import annotations

import csv
import io
import json
import logging
import os
from collections import Counter

from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator, MaxValueValidator, MinValueValidator
from django.db import connection, models
from django.urls import reverse
from django.utils import timezone
from django.utils.functional import cached_property
from django_extensions.db.models import ActivatorModel, TimeStampedModel, TitleSlugDescriptionModel
from libgravatar import Gravatar
from upload_validator import FileTypeValidator

import stats
from enrich.models import BingAPILookup, BingAPITranslation
from enrich.translate.bing import BingTranslator
from ndutils import user_imports_path, user_resources_path
from zhhans_en.translate.ccc import ZHHANS_EN_CCCedictTranslator

from .validators import validate_file_size

MANIFEST_JSON = "manifest.json"
PARSE_JSON_SUFFIX = ".parse.json"
ENRICH_JSON_SUFFIX = ".enrich.json"
DATA_JS_SUFFIX = ".data.js"
SRT_EXTENTION = ".srt"
VTT_EXTENTION = ".vtt"
WEBVTT_FILE = "subtitles.vtt"


SIMPLIFIED_UTF8_ORD_MIN = 22909
SIMPLIFIED_UTF8_ORD_MAX = 40869

logger = logging.getLogger(__name__)

NONE = 0
REQUESTED = 1
PROCESSING = 2
FINISHED = 3
ERROR = 4

PROCESSING_STATUS = [
    (NONE, "None"),
    (REQUESTED, "Requested"),
    (PROCESSING, "Processing"),
    (FINISHED, "Finished"),
    (ERROR, "ERROR"),
]


class Card(models.Model):
    L2_GRAPH = 1
    L2_SOUND = 2
    L1_MEANING = 3

    CARD_TYPE = [
        (L2_GRAPH, "L2 written form"),  # JS GRAPH
        (L2_SOUND, "L2 sound form"),  # JS SOUND
        (L1_MEANING, "L1 meaning"),  # JS MEANING
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, help_text="Card owner")
    word = models.ForeignKey(BingAPILookup, on_delete=models.CASCADE)
    card_type = models.IntegerField(choices=CARD_TYPE, default=L2_GRAPH, help_text="Card type")
    interval = models.IntegerField(default=0, help_text="SM2 interval")
    repetition = models.IntegerField(default=0, help_text="SM2 repetition")
    efactor = models.FloatField(default=2.5, help_text="SM2 efactor")
    front = models.TextField(null=True, help_text="Override default definition cue")
    back = models.TextField(null=True, help_text="Override default definition expected response")
    due_date = models.DateTimeField(null=True)
    first_revision_date = models.DateTimeField(null=True)
    last_revision_date = models.DateTimeField(null=True)
    updated_at = models.DateTimeField(default=timezone.now)
    known = models.BooleanField(default=False, help_text="Learner believes they 'know' the word/cardtype")
    suspended = models.BooleanField(default=False, help_text="Don't revise the cardtype")
    deleted = models.BooleanField(default=False, help_text="Card has been deleted")


class Transcrober(models.Model):
    # FIXME: move this class to the transcrobes app
    DARK_MODE = "dark"
    LIGHT_MODE = "light"
    WHITE_MODE = "white"
    BLACK_MODE = "black"

    CONTENT_MODE = [
        (DARK_MODE, "Dark mode"),
        (LIGHT_MODE, "Light mode"),
        (WHITE_MODE, "White mode"),
        (BLACK_MODE, "Black mode"),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    # TODO: this should probably be a OneToMany, so we can have users
    # who use the system for more than one language. KISS for the moment
    from_lang = models.CharField(max_length=20, default="zh-Hans")  # 20 is probably overkill
    to_lang = models.CharField(max_length=20, default="en")  # 20 is probably overkill

    # FIXME: this is pretty nasty, but while we are defaulting to from_lang="zh-Hans", why not!
    ds = f"{BingTranslator.SHORT_NAME},{ZHHANS_EN_CCCedictTranslator.SHORT_NAME},{BingTranslator.FALLBACK_SHORT_NAME}"
    dictionary_ordering = models.CharField(max_length=50, default=ds)

    default_segment = models.BooleanField(default=True, help_text="Segment texts by default")
    default_glossing = models.IntegerField(
        choices=stats.USER_GLOSSING_MODE,
        default=stats.GLOSSING_MODE_L1,
        help_text="Default gloss mode for platform-internal reading",
    )
    reading_mode = models.CharField(
        choices=CONTENT_MODE, max_length=100, default=DARK_MODE, help_text="Reading mode for platform-internal reading"
    )
    font_size_percent = models.IntegerField(
        validators=[MinValueValidator(30), MaxValueValidator(200)], default=100, help_text="Default font size percent"
    )
    subtitle_default_segment = models.BooleanField(default=True, help_text="Segment subtitles by default")
    subtitle_default_glossing = models.IntegerField(
        choices=stats.USER_GLOSSING_MODE,
        default=stats.GLOSSING_MODE_L1,
        help_text="Default gloss mode for platform-internal subtitles",
    )
    media_mode = models.CharField(
        choices=CONTENT_MODE, max_length=100, default=DARK_MODE, help_text="Video mode for platform-internal subtitles"
    )
    subtitle_box_width_percent = models.IntegerField(
        validators=[MinValueValidator(25), MaxValueValidator(100)],
        default=50,
        help_text="Default subtitle box width percent",
    )
    subtitle_font_size_percent = models.IntegerField(
        validators=[MinValueValidator(30), MaxValueValidator(250)],
        default=150,
        help_text="Default subtitle font size percent",
    )

    @staticmethod
    def get_absolute_url():
        return reverse("profile")

    def lang_pair(self):
        return f"{self.from_lang}:{self.to_lang}"

    def get_gravatar(self):
        return Gravatar(self.user.email).get_image()[5:]  # remove the 'http:'

    def get_full_name(self):
        full_name = f"{self.user.first_name} {self.user.last_name}"
        return full_name if full_name.strip() else self.user.username

    @cached_property
    def known_words(self):
        return set(
            BingAPILookup.objects.filter(userword__user=self.user, userword__is_known=True).values_list(
                "source_text", flat=True
            )
        )

    @cached_property
    def known_word_bases(self):
        # TODO: are these morphemes? sorta? it basically means "Chinese characters" but that's not very generic :-)
        return Counter("".join(self.known_words))

    def filter_known(self, words, min_morpheme_known_count=2, prefer_whole_known_words=True):
        if not words:
            return []  # or None?
        known = []
        whole_known_words = []
        for word in words:
            if word in self.known_words:
                if prefer_whole_known_words:
                    whole_known_words.append(word)
                else:
                    known.append(word)
            elif min_morpheme_known_count > 0:
                good = True
                for character in word:
                    if (
                        character not in self.known_word_bases
                        or self.known_word_bases[character] < min_morpheme_known_count
                    ):
                        good = False
                        break
                if good:
                    known.append(word)

        logger.debug(f"{whole_known_words + known=}")

        return whole_known_words + known

    def user_onboarded(self):
        ids = settings.USER_ONBOARDING_SURVEY_IDS
        return self.usersurvey_set.filter(survey__id__in=ids).count() == len(ids)


class DetailedModel(ActivatorModel, TimeStampedModel, TitleSlugDescriptionModel):
    def __str__(self):
        return f"{self.title}"

    class Meta:
        abstract = True


class DetailedProcessingModel(DetailedModel):
    class Meta:
        abstract = True

    def processing_status(self):
        if self.processing == FINISHED:
            return "Processed"

        if self.processing in [PROCESSING, REQUESTED]:
            return "Processing"

        if self.processing in [ERROR]:
            return "Error"

        return "None"


class Import(DetailedProcessingModel):
    VOCABULARY_ONLY = 1
    GRAMMAR_ONLY = 2
    VOCABULARY_GRAMMAR = 3
    PROCESS_TYPE = [
        (VOCABULARY_ONLY, "Vocabulary Only"),
        (GRAMMAR_ONLY, "Grammar Only"),
        (VOCABULARY_GRAMMAR, "Vocabulary and Grammar"),
    ]

    process_type = models.IntegerField(choices=PROCESS_TYPE, default=VOCABULARY_ONLY, help_text="What items to extract")
    user = models.ForeignKey(User, on_delete=models.CASCADE, help_text="Import owner")
    import_file = models.FileField(
        upload_to=user_imports_path,
        validators=[
            FileTypeValidator(
                allowed_types=["text/plain", "text/csv", "application/csv", "application/zip", "application/epub+zip"]
            ),
            FileExtensionValidator(allowed_extensions=["txt", "csv", "epub", "vtt", "srt"]),
            validate_file_size,
        ],
        help_text="File to import",
    )

    # TODO: think about alerting if the object modification time is too old and processed = null
    processing = models.IntegerField(choices=PROCESSING_STATUS, default=REQUESTED, help_text="Processing status")

    # TODO: maybe use a JSONField? It's JSON but we likely don't need the overhead in the db
    analysis = models.TextField(null=True)

    # shared, can be seen by others, and used as a template for creating their own versions
    shared = models.BooleanField(default=False, help_text="Allow others to see and use this import?")

    def processed(self):
        return self.processing == FINISHED

    def _relative_processed_path(self):
        return user_resources_path(self.user, os.path.basename(self.import_file.path))

    def processed_path(self):
        return os.path.join(settings.MEDIA_ROOT, self._relative_processed_path())

    def import_file_name(self):
        return os.path.basename(self.import_file.name)

    # FIXME: document that this is NOT the complete list, and consider adding the complete list instead
    # In our resulting parse we ignore several catgories of word and therefore none of the nb_useful_*
    # methods have a complete list. We should probably have *everything* available in terms of stats -
    # meaning we also take all the CD, NT, etc. pos and filter later for various counts. We almost certainly
    # won't want them in the lists but the point of having separate Import, UserList and Goal is precisely so
    # we have freedom around this!!!
    def nb_useful_types(self):
        if not self.analysis:
            return "Waiting"
        counts = json.loads(self.analysis)["vocabulary"]["counts"]
        return sum(counts.values())

    def nb_useful_tokens(self):
        if not self.analysis:
            return "Waiting"
        counts = json.loads(self.analysis)["vocabulary"]["counts"]
        return sum([int(k) * v for k, v in counts.items()])

    def nb_useful_characters_total(self):
        if not self.analysis:
            return "Waiting"
        words = json.loads(self.analysis)["vocabulary"]["buckets"]
        return sum([int(k) * len("".join(v)) for k, v in words.items()])

    def nb_useful_characters_unique(self):
        if not self.analysis:
            return "Waiting"
        words = json.loads(self.analysis)["vocabulary"]["buckets"]
        # a long string into a set to get only unique chars
        all_unique_characters = set("".join(["".join(v) for v in words.values()]))
        # then make sure that we only count Chinese/Simplified characters
        return len(
            [
                x
                for x in all_unique_characters
                if ord(x) >= SIMPLIFIED_UTF8_ORD_MIN and ord(x) <= SIMPLIFIED_UTF8_ORD_MAX
            ]
        )

    def get_absolute_url(self):
        return reverse("import_detail", args=[str(self.id)])


class Content(DetailedProcessingModel):
    BOOK = 1
    VIDEO = 2
    # AUDIOBOOK = 3
    # MUSIC = 4
    # MANGA = 5
    CONTENT_TYPE = [
        (BOOK, "Book"),
        (VIDEO, "Video"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, help_text="Content owner")
    the_import = models.OneToOneField(Import, on_delete=models.CASCADE, help_text="Source import")

    # TODO: think about alerting if the object modification time is too old and processed = null
    processing = models.IntegerField(choices=PROCESSING_STATUS, default=NONE, help_text="Processed status")

    content_type = models.IntegerField(choices=CONTENT_TYPE, default=BOOK, help_text="Type of content")
    author = models.CharField(max_length=150, null=True, blank=True)
    cover = models.CharField(max_length=250, null=True, blank=True)
    language = models.CharField(max_length=30, null=True, blank=True)

    # shared, can be used by others
    shared = models.BooleanField(default=False, help_text="Allow others to see and use this content?")

    def _relative_processed_path(self):
        return user_resources_path(self.user, self.id)

    def processed_path(self):
        return os.path.join(settings.MEDIA_ROOT, self._relative_processed_path())

    def get_absolute_url(self):
        return reverse("content_detail", args=[str(self.id)])

    def get_entry_point_url(self):
        entry_file = MANIFEST_JSON if self.content_type == Content.BOOK else WEBVTT_FILE
        return reverse("webpub_serve", args=[str(self.id), entry_file])


class Survey(DetailedModel):
    survey_json = models.JSONField()
    users = models.ManyToManyField(User, through="UserSurvey")
    is_obligatory = models.BooleanField(default=False)


class UserSurvey(TimeStampedModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    survey = models.ForeignKey(Survey, on_delete=models.CASCADE)
    data = models.JSONField(null=True)

    def __str__(self):
        return f"{self.user} - {self.survey.title}"

    class Meta:
        unique_together = [["user", "survey"]]


class Source(models.Model):
    name = models.CharField(max_length=100)
    sub_name = models.CharField(max_length=100, null=True, blank=True)

    def __str__(self):
        return f"{self.name}:{self.sub_name}"


class GrammarRule(models.Model):
    name = models.CharField(max_length=1000)
    rule = models.CharField(max_length=1000)  # BA, BEI, etc.
    hsk_id = models.CharField(max_length=1000, null=True, blank=True)  # 3.20.1, 4.10, etc. directly from the book
    hsk_sub_id = models.CharField(max_length=1000, null=True, blank=True)  # when HSK underspecifies, add a, b, c, etc.
    help_url = models.CharField(max_length=1000, null=True, blank=True)
    topic_id = models.IntegerField()  # this might be better as a table rather than a const in another project...

    def __str__(self):
        return f'{self.hsk_id}-{self.hsk_sub_id if self.hsk_sub_id else ""} - {self.name} - {self.rule}'

    def get_absolute_url(self):
        return reverse("rule_detail", kwargs={"pk": self.pk})

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["hsk_id", "hsk_sub_id"], name="hsk_id_sub_id"),
        ]


class SText(models.Model):
    source = models.ForeignKey(Source, on_delete=models.CASCADE)
    source_subid = models.IntegerField()  # question for HSK, xls line for textbooks

    def grammar_rules(self):
        rlz = []
        for s in self.sentence_set.prefetch_related("grammar_rules").all():
            rlz += s.grammar_rules.all()
        return rlz

    def __str__(self):
        return f"{self.source}:{self.source_id}"

    def first_sentence(self):
        return self.sentence_set.order_by("sorder").first()  # self.sentence_set

    def nbchars(self):
        nb = 0
        for i in self.sentence_set.all():
            nb += len(i.content)
        return nb

    def get_absolute_url(self):
        return reverse("stext_detail", kwargs={"pk": self.pk})


class UserTextEvaluation(models.Model):
    VERY_EASY = -2
    EASY = -1
    OK = 0
    HARD = 1
    VERY_HARD = 2
    DIFFICULTY_CHOICES = [
        (VERY_EASY, "Very easy"),
        (EASY, "Easy"),
        (OK, "Just right"),
        (HARD, "Hard"),
        (VERY_HARD, "Very hard"),
    ]
    difficulty = models.IntegerField(
        choices=DIFFICULTY_CHOICES,
        default=OK,
    )
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    text = models.ForeignKey(SText, on_delete=models.CASCADE)
    date_read = models.DateTimeField(default=timezone.now)


class Sentence(models.Model):
    text = models.ForeignKey(SText, on_delete=models.CASCADE)
    sorder = models.IntegerField()
    # content
    content = models.TextField()
    # analysis
    parse = models.TextField()
    grammar_rules = models.ManyToManyField(GrammarRule)
    vocab1 = models.IntegerField()
    vocab2 = models.IntegerField()
    vocab3 = models.IntegerField()
    vocab4 = models.IntegerField()
    vocab5 = models.IntegerField()
    vocab6 = models.IntegerField()
    vocab7 = models.IntegerField()

    def __str__(self):
        return str(self.content)

    def separated(self):
        return " ".join([f"{t['word']}" for t in json.loads(self.parse)["tokens"]])


class SentenceWords(models.Model):
    sentence = models.ForeignKey(Sentence, on_delete=models.CASCADE)
    word = models.ForeignKey(BingAPILookup, on_delete=models.CASCADE)
    index = models.IntegerField()
    pos = models.CharField(max_length=3)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["sentence", "word", "index", "pos"], name="sentence_word"),
        ]


class UserSentenceEvaluation(models.Model):
    VERY_EASY = -2
    EASY = -1
    OK = 0
    HARD = 1
    VERY_HARD = 2
    DIFFICULTY_CHOICES = [
        (VERY_EASY, "Very easy"),
        (EASY, "Easy"),
        (OK, "Just right"),
        (HARD, "Hard"),
        (VERY_HARD, "Very hard"),
    ]
    difficulty = models.IntegerField(
        choices=DIFFICULTY_CHOICES,
        default=OK,
    )
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    sentence = models.ForeignKey(Sentence, on_delete=models.CASCADE)
    date_read = models.DateTimeField(default=timezone.now)


class UserSentence(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    # FIXME: this is a horrible hack due to the fact that we know all sentences get translated on Bing
    # so they will be checked in all analyses. This will likely cause huge issues later and a
    # bespoke class/table for this should be created!!!
    sentence = models.ForeignKey(BingAPITranslation, on_delete=models.CASCADE)

    nb_seen = models.IntegerField(default=0)
    last_seen = models.DateTimeField(default=timezone.now)
    nb_seen_since_last_check = models.IntegerField(default=0)  # FIXME: done in a trigger???

    nb_translated = models.IntegerField(default=0)
    last_translated = models.DateTimeField(default=timezone.now)


class UserWord(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    # FIXME: this is a horrible hack due to the fact that we know all words get looked up on Bing
    # so they will be checked in all analyses. This will likely cause huge issues later and a
    # bespoke class/table for this should be created!!!
    word = models.ForeignKey(BingAPILookup, on_delete=models.CASCADE)

    # FIXME:
    # this is a blunt instrument designed for active testing - if you get an answer to
    # a question specifically testing for this, you know it. There are obviously many
    # dimensions to knowing a word, so it should be at least a scale, even for explicit
    # tests. This should also be able interact with other evidence gathered for knowledge,
    # like looking at the last_checked and last_studied, which could possibly devalidate
    # the known status...
    is_known = models.BooleanField(null=True)

    # FIXME:
    # we really need these to come from a huge datastore with each event - best would be to have
    # things like nb_seen_since_last_check and other cool things like detecting the time since
    # last seen before a new check, allowing predicting forgetting
    nb_seen = models.IntegerField(default=0)
    last_seen = models.DateTimeField(default=timezone.now)
    nb_seen_since_last_check = models.IntegerField(default=0)  # FIXME: done in a trigger???
    nb_checked = models.IntegerField(default=0)
    last_checked = models.DateTimeField(null=True)
    # FIXME: these are intended to come from sentence (see 'sids' in the view translations, NOT from normal
    # lookups, which are what the *_checked correspond to
    nb_translated = models.IntegerField(null=True)
    last_translated = models.DateTimeField(null=True)
    updated_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "word"], name="user_word"),
        ]


class UserGrammarRule(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    grammar_rule = models.ForeignKey(GrammarRule, on_delete=models.CASCADE)

    # FIXME:
    # this is a blunt instrument designed for active testing - if you get an answer to
    # a question specifically testing for this, you know it. There are obviously many
    # dimensions to knowing a rule, so it should be at least a scale, even for explicit
    # tests. This should also be able interact with other evidence gathered for knowledge,
    # like looking at the last_checked and last_studied, which could possibly devalidate
    # the known status...
    is_known = models.BooleanField(null=True)

    # FIXME:
    # we really need these to come from a huge datastore with each event - best would be to have
    # things like nb_seen_since_last_check and other cool things like detecting the time since
    # last seen before a new check, allowing predicting forgetting
    nb_seen = models.IntegerField(default=0)
    last_seen = models.DateTimeField(default=timezone.now)
    nb_seen_since_last_check = models.IntegerField(default=0)  # FIXME: done in a trigger???
    nb_checked = models.IntegerField(default=0)
    last_checked = models.DateTimeField(null=True)
    nb_seen_since_last_study = models.IntegerField(default=0)  # FIXME: done in a trigger???
    nb_studied = models.IntegerField(default=0)
    last_studied = models.DateTimeField(null=True)

    # FIXME: these are intended to come from sentence (see 'sids' in the view translations, NOT from normal
    # lookups, which are what the *_checked correspond to
    # nb_translated = models.IntegerField(default=0)
    # last_translated = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.user} : {self.grammar_rule}"

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "grammar_rule"], name="user_rule"),
        ]


class UserList(DetailedProcessingModel):
    ABSOLUTE_FREQUENCY = 0
    IMPORT_FREQUENCY = 1
    # A mix of the two? With a weight?
    ORDER_BY_CHOICES = [
        (ABSOLUTE_FREQUENCY, "Absolute Frequency"),
        (IMPORT_FREQUENCY, "Frequency in import"),
    ]

    user = models.ForeignKey(User, null=True, on_delete=models.CASCADE)
    the_import = models.ForeignKey(
        Import, on_delete=models.CASCADE, help_text="The import to create the list from", null=True
    )

    # shared, can be seen by others, and used as a template for creating their own versions
    shared = models.BooleanField(default=False, help_text="Allow others to see and use this list?")

    # Filters
    nb_to_take = models.IntegerField(
        default=-1, help_text="Maximum number of words in the list, -1 for all"
    )  # -1 = all
    order_by = models.IntegerField(
        choices=ORDER_BY_CHOICES,
        default=ABSOLUTE_FREQUENCY,
        help_text="Order of the words (only useful when a maximum number is specified)",
    )
    only_dictionary_words = models.BooleanField(
        default=True, help_text="Ignore words that don't appear in the main dictionary"
    )
    minimum_doc_frequency = models.IntegerField(
        default=-1,
        help_text="Min occurrences in the import before the word will be added to the list, -1 for all",
    )
    minimum_abs_frequency = models.IntegerField(
        default=-1,
        help_text=("Minimum frequency in words per million, see the documentation for more details, -1 for all"),
    )

    # FIXME: should we allow a choice here? what are some genuinely useful examples?
    only_simplifieds = True
    # only_simplifieds = models.BooleanField(default=True)

    # state
    processing = models.IntegerField(choices=PROCESSING_STATUS, default=REQUESTED, help_text="Processed status")

    # actions
    words_are_known = models.BooleanField(default=False, help_text="Should the words added be set to already known?")

    def get_absolute_url(self):
        return reverse("list_detail", args=[str(self.id)])

    def list_length(self):
        return UserListWord.objects.filter(user_list=self).count()

    def filter_words(self, import_frequencies):
        # FIXME: nasty hardcoding
        # abs_frequency_table = manager.metadata()[1]  # 0 = HSK, 1 = Subtlex
        word_list = list()
        for freq, words in import_frequencies["vocabulary"]["buckets"].items():
            # if freq < self.minimum_doc_frequency:
            #     continue

            new_list = []
            for word in words:
                # if self.minimum_abs_frequency > 0:
                #     abs_frequency = self.minimum_abs_frequency < abs_frequency_table.get(word)
                #     # wcpm = word count per million
                #     if not abs_frequency or abs_frequency[0]['wcpm'] < self.minimum_abs_frequency:
                #         continue

                if self.only_simplifieds:
                    # https://stackoverflow.com/questions/1366068/whats-the-complete-range-for-chinese-characters-in-unicode
                    # we are missing some here but it's better than nothing
                    #
                    # \u4e00 == 22909 in base10 and \u9fa5 = 40869
                    # these are the values used in enrichers.zhhans.__init__, which we are reusing
                    # FIXME: use a single value for both these!
                    for character in word:
                        if ord(character) >= SIMPLIFIED_UTF8_ORD_MIN and ord(character) <= SIMPLIFIED_UTF8_ORD_MAX:
                            new_list.append(word)
                            break
            word_list += [(freq, word) for word in new_list]

        return word_list

    def publish_updates(self, cards_updated: bool):
        stats.KAFKA_PRODUCER.send("word_list", str(self.user.id))
        if self.words_are_known and cards_updated:
            stats.KAFKA_PRODUCER.send("cards", str(self.user.id))

    # FIXME: why does this not work????
    # async def publish_updates(self, cards_updated: bool):
    #     broadcast = await get_broadcast()
    #     # await broadcast.publish(channel=f"word_list-{self.user.id}", message=1)
    #     await broadcast.publish(channel="word_list", message=str(self.user.id))
    #     if self.words_are_known and cards_updated:
    #         await broadcast.publish(channel="cards", message=str(self.user.id))

    def update_list_words(self, manager):  # noqa:C901 # pylint: disable=R0914,R0915
        import_frequencies = json.loads(self.the_import.analysis)
        word_list = self.filter_words(import_frequencies)

        logger.info(
            f"Processing {len(word_list)} words in update_list_words"
            f" for UserList {self.id} for user {self.user.username}"
        )

        temp_file = io.StringIO()
        writer = csv.writer(temp_file, delimiter="\t")
        for freq, word in word_list:
            writer.writerow([word, freq, None, None])

        temp_file.seek(0)  # will be empty otherwise!!!
        with connection.cursor() as cur:
            temp_table = f"import_{self.id}"
            sql = f"""
                CREATE TEMP TABLE {temp_table} (word text,
                                                import_frequency int,
                                                word_id int null,
                                                freq float null
                                                )"""

            # FIXME: this algorithm needs some serious optimisation!!!

            cur.execute(sql)

            # Fill database temp table from the CSV
            cur.copy_from(temp_file, temp_table, null="")
            # Get the ID for each word from the reference table (currently enrich_bingapilookup)
            cur.execute(
                f"""UPDATE {temp_table}
                    SET word_id = enrich_bingapilookup.id
                    FROM enrich_bingapilookup
                    WHERE word = enrich_bingapilookup.source_text"""
            )

            cur.execute(
                f"""UPDATE {temp_table}
                    SET freq = ((enrichers_zh_subtlexlookup.response_json::json->0)::jsonb->>'wcpm')::float
                    FROM enrichers_zh_subtlexlookup
                    WHERE word = enrichers_zh_subtlexlookup.source_text"""
            )

            sql = f"SELECT word FROM {temp_table} WHERE word_id IS NULL"

            # filtering - this is slow and we have limits, so only get what we really need NOW (we
            # can always get others later)
            filters = []
            if self.minimum_abs_frequency > 0:
                filters += [f"{temp_table}.freq > {self.minimum_abs_frequency}"]
            if self.minimum_doc_frequency > 0:
                filters += [f"{temp_table}.import_frequency > {self.minimum_doc_frequency}"]

            sql += (" AND " + " AND ".join(filters)) if filters else ""
            cur.execute(sql)

            new_words = cur.fetchall()

            logger.info(
                f"Creating ref entries for {len(new_words)} system-unknown words in update_list_words"
                f" for UserList {self.id} for user {self.user.username}"
            )

            for word in new_words:
                # TODO: this is a nasty hack with a side effect of creating bing_lookups, which are
                # our reference values, thus ensuring that all words in the import exist in the db
                token = {"word": word[0], "pos": "NN", "lemma": word[0]}
                manager.default().get_standardised_defs(token)

            if new_words:
                sql = f"""UPDATE {temp_table}
                          SET word_id = enrich_bingapilookup.id
                          FROM enrich_bingapilookup
                          WHERE word = enrich_bingapilookup.source_text
                              AND from_lang = %s AND to_lang = %s"""
                cur.execute(sql, self.user.transcrober.from_lang, self.user.transcrober.to_lang)

            sql = f"""
                SELECT word_id
                FROM {temp_table}
                    INNER JOIN enrich_bingapilookup ON enrich_bingapilookup.id = word_id """

            if self.only_dictionary_words:  # FIXME: this should include the other dictionaries also!!!
                filters += ["json_array_length(enrich_bingapilookup.response_json::json->0->'translations') > 0"]

            sql += (" WHERE " + " AND ".join(filters)) if filters else ""

            # TODO: make more generic
            if self.order_by == self.ABSOLUTE_FREQUENCY:
                sql += f" ORDER BY {temp_table}.freq DESC "
            else:
                sql += f" ORDER BY {temp_table}.import_frequency DESC "

            sql += f" LIMIT {self.nb_to_take} " if self.nb_to_take > 0 else ""

            cur.execute(sql)

            new_userwords = []
            new_userlistwords = []
            for i, word_id in enumerate(cur.fetchall()):
                new_userwords.append(UserWord(user=self.user, word_id=word_id[0]))
                new_userlistwords.append(UserListWord(user_list=self, word_id=word_id[0], default_order=i))

            # bulk create using objects
            # TODO: if this is slow due to ignore_conflicts, maybe update with the id
            # before doing this and only select those without an id
            UserWord.objects.bulk_create(new_userwords, ignore_conflicts=True)
            UserListWord.objects.bulk_create(new_userlistwords, ignore_conflicts=True)  # can there be conflicts?

            logger.info(f"Added {len(new_userlistwords)} list words for user_list_{self.id} for {self.user.username}")
            new_cards = []
            if self.words_are_known:
                # FIXME: make this not so ugly
                for ul_word in UserListWord.objects.filter(user_list=self):
                    for card_type in Card.CARD_TYPE:
                        new_cards.append(
                            Card(
                                user=self.user,
                                word=ul_word.word,
                                card_type=card_type,
                                known=self.words_are_known,
                            )
                        )

                Card.objects.bulk_create(new_cards, ignore_conflicts=True)

            cur.execute(f"DROP TABLE {temp_table}")
            # FIXME: the async version doesn't work :-(
            # asyncio.run(self.publish_updates((len(new_cards) > 0)))
            self.publish_updates((len(new_cards) > 0))


class UserListGrammarRule(models.Model):
    user_list = models.ForeignKey(UserList, on_delete=models.CASCADE)
    grammar_rule = models.ForeignKey(GrammarRule, on_delete=models.CASCADE)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user_list", "grammar_rule"], name="user_list_rule"),
        ]


class UserListWord(models.Model):
    user_list = models.ForeignKey(UserList, on_delete=models.CASCADE)
    word = models.ForeignKey(BingAPILookup, on_delete=models.CASCADE)
    default_order = models.IntegerField(default=0)  # FIXME: shouldn't be a default?

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user_list", "word"], name="user_list_word"),
        ]


class Goal(DetailedModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    user_list = models.ForeignKey(UserList, on_delete=models.CASCADE, null=True, blank=True)
    parent = models.ForeignKey("self", related_name="children", on_delete=models.CASCADE, null=True, blank=True)
    priority = models.IntegerField(choices=[(i, i) for i in range(1, 10)], default=5)

    def get_absolute_url(self):
        return reverse("goal_detail", args=[str(self.id)])

    def sub_goal_names(self):
        return [x.title for x in self.children.active()]

    def get_progress(self):
        # FIXME: convert to ORM
        known_words, all_words = 0, 0
        if self.user_list:
            sql = """
                SELECT COUNT(NULLIF(uw.is_known, FALSE)), COUNT(0)
                FROM data_userlistword uwl
                    INNER JOIN data_userword uw ON uw.word_id = uwl.word_id
                WHERE uwl.user_list_id = %s"""
            with connection.cursor() as cur:
                cur.execute(sql, (self.user_list.id,))
                known_words, all_words = cur.fetchone()

        chidlins = self.children.active()
        if chidlins.count() > 0:
            sum_progress = [sum(x) for x in zip(*[y.get_progress() for y in chidlins])]
            known_words += sum_progress[0]
            all_words += sum_progress[1]

        return known_words, all_words

    def get_progress_percent(self):
        known_words, all_words = self.get_progress()
        # return f"{(known_words*100/all_words):.0f}" if all_words else ""
        return (known_words / all_words) if all_words else None

    # override Model.clean_fields()
    def clean_fields(self, exclude=None):
        if self.has_cycle():
            raise ValidationError("Cycle detected. A goal cannot have itself as a parent!")

    # override Model.save()
    def save(self, *args, **kwargs):
        if self.has_cycle():
            raise ValidationError("Cycle detected. A goal cannot have itself as a parent!")
        return super().save(*args, **kwargs)

    def has_cycle(self):
        if not self.parent:
            return False
        if self.parent == self:
            return True
        the_parent = self.parent
        while the_parent:
            if the_parent == self:
                return True
            the_parent = the_parent.parent

        return False
