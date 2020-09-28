# -*- coding: utf-8 -*-
import json

from django.conf import settings
from django.contrib.auth.models import User
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django_extensions.db.models import ActivatorModel, TimeStampedModel, TitleSlugDescriptionModel

from enrich.models import BingAPILookup, BingAPITranslation


class Survey(ActivatorModel, TitleSlugDescriptionModel, TimeStampedModel):
    survey_json = models.JSONField()
    users = models.ManyToManyField(User, through="UserSurvey")
    is_obligatory = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.title}"


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
        return reverse("rule-detail", kwargs={"pk": self.pk})

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
        return reverse("stext-detail", kwargs={"pk": self.pk})


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
    difficulty = models.IntegerField(choices=DIFFICULTY_CHOICES, default=OK,)
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

    # words = models.ManyToManyField(BingAPILookup)

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
    difficulty = models.IntegerField(choices=DIFFICULTY_CHOICES, default=OK,)
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
    # FIXME: these are intended to come from sentence (see 'sids' in the view translations, NOT from normal
    # lookups, which are what the *_checked correspond to
    nb_translated = models.IntegerField(null=True)
    last_translated = models.DateTimeField(null=True)

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
