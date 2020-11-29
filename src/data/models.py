# -*- coding: utf-8 -*-
import csv
import io
import json

from django.conf import settings
from django.contrib.auth.models import User
from django.core.validators import FileExtensionValidator
from django.db import connection, models
from django.urls import reverse
from django.utils import timezone
from django_extensions.db.models import ActivatorModel, TimeStampedModel, TitleSlugDescriptionModel
from upload_validator import FileTypeValidator

from enrich.models import BingAPILookup, BingAPITranslation

from .validators import validate_file_size


class DetailedModel(ActivatorModel, TimeStampedModel, TitleSlugDescriptionModel):
    class Meta:
        abstract = True


def user_directory_path(instance, filename):
    # file will be uploaded to MEDIA_ROOT/imports/user_<id>/<filename>
    return "imports/user_{0}/{1}".format(instance.user.id, filename)


class Import(DetailedModel):
    VOCABULARY_ONLY = 1
    GRAMMAR_ONLY = 2
    VOCABULARY_GRAMMAR = 3
    PROCESS_TYPE = [
        (VOCABULARY_ONLY, "Vocabulary Only"),
        (GRAMMAR_ONLY, "Grammar Only"),
        (VOCABULARY_GRAMMAR, "Vocabulary and Grammar"),
    ]

    process_type = models.IntegerField(choices=PROCESS_TYPE, default=VOCABULARY_ONLY)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    import_file = models.FileField(
        upload_to=user_directory_path,
        validators=[
            FileTypeValidator(allowed_types=["text/plain", "text/csv", "application/csv"]),
            FileExtensionValidator(allowed_extensions=["txt", "csv"]),
            validate_file_size,
        ],
    )

    # TODO: think about alerting if the object modification time is too old and processed = null
    processed = models.BooleanField(default=False, null=True)  # False = new, null = processing, True = processed

    # TODO: maybe use a JSONField? It's JSON but we likely don't need the overhead in the db
    analysis = models.TextField(null=True)

    def __str__(self):
        return f"{self.title}"

    def get_absolute_url(self):
        return reverse("import_detail", args=[str(self.id)])


class Survey(DetailedModel):
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


class UserList(DetailedModel):
    # FIXME: implement ordering by different frequencies
    ABSOLUTE_FREQUENCY = 0
    IMPORT_FREQUENCY = 1
    # A mix of the two? With a weight?
    ORDER_BY_CHOICES = [
        (ABSOLUTE_FREQUENCY, "Absolute Frequency"),
        (IMPORT_FREQUENCY, "Frequency in import"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    the_import = models.ForeignKey(Import, on_delete=models.CASCADE)

    # Filters
    nb_to_take = models.IntegerField(default=-1)  # -1 = all
    order_by = models.IntegerField(
        choices=ORDER_BY_CHOICES,
        default=ABSOLUTE_FREQUENCY,
    )
    order_by = IMPORT_FREQUENCY

    # FIXME: should we allow a choice here?
    only_simplifieds = True
    # only_simplifieds = models.BooleanField(default=True)

    only_dictionary_words = models.BooleanField(default=True)

    # FIXME: implement
    minimum_frequency = models.IntegerField(default=-1)  # -1 = all

    # state
    processed = models.BooleanField(default=False, null=True)  # False = new, null = processing, True = processed

    # actions
    add_notes = models.BooleanField(default=False)
    notes_are_known = models.BooleanField(default=False)

    def update_list_words(self, manager):
        if self.processed is None:  # currently updating elsewhere?
            return

        import_frequencies = json.loads(self.the_import.analysis)
        # word_list = []
        # if self.order_by == IMPORT_FREQUENCY:
        #     word_list = list(chain.from_iterable(v for k,v in sorted(import_frequencies.items(), reverse=True)))
        # # elif...:
        # #     order by other stuff
        # else:
        #     word_list = list(chain.from_iterable(import_frequencies.items()))

        if self.only_simplifieds:
            # new_list = []
            # https://stackoverflow.com/questions/1366068/whats-the-complete-range-for-chinese-characters-in-unicode
            # we are missing some here but it's better than nothing
            #
            # \u4e00 == 22909 in base10 and \u9fa5 = 40869
            # these are the values used in enrichers.zhhans.__init__, which we are reusing
            # FIXME: use a single value for both these!
            word_list = list()
            for freq, words in import_frequencies["vocabulary"]["buckets"].items():
                new_list = []
                for word in words:
                    for character in word:
                        if ord(character) >= 22909 and ord(character) <= 40869:
                            new_list.append(word)
                            break
                word_list += [(freq, word) for word in new_list]
                # new_frequencies[freq] = new_list

            # for word in word_list:
            #     for character in word:
            #         if ord(character) >= 22909 and ord(character) <= 40869:
            #             new_list.append(word)
            #             break

            # word_list = new_list

        temp_file = io.StringIO()
        writer = csv.writer(temp_file, delimiter="\t")
        for word, freq in word_list:
            writer.writerow([word, freq, None, None])

        temp_file.seek(0)  # will be empty otherwise!!!
        with connection.cursor() as cur:
            temp_table = f"import_{self.id}"
            sql = f"""
                CREATE TEMP TABLE {temp_table} (word text,
                                                import_frequency int,
                                                word_id int null,
                                                freq float null,
                                                user_word_id int null
                                                )"""
            # FIXME: this needs some serious optimisation!!!

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

            cur.execute(f"SELECT word FROM import_{self.id} WHERE word_id IS NULL")
            for word in cur.fetchall():
                # TODO: this is a nasty hack with a side effect of creating bing_lookups, which are
                # our reference values
                token = {"word": word, "pos": "NN", "lemma": word}
                manager.default().get_standardised_defs(token)

            cur.execute(
                f"""UPDATE {temp_table}
                                SET word_id = enrich_bingapilookup.id
                                FROM enrich_bingapilookup
                                WHERE word = enrich_bingapilookup.source_text"""
            )

            cur.execute(
                f"""INSERT INTO data_userword (user_id, word_id)
                                SELECT {self.user_id}, word_id from {temp_table}
                                WHERE word = enrich_bingapilookup.source_text
                                ON CONFLICT (user_id, word_id) DO NOTHING"""
            )

            cur.execute(
                f"""UPDATE {temp_table} tt
                                SET user_word_id = data_userword.id
                                FROM data_userword
                                WHERE tt.word_id = data_userword.word_id"""
            )

            sql = f"""
                INSERT INTO data_userlistword (user_list_id, user_word_id)
                                SELECT {self.id}, id from data_userword dw
                                inner join {temp_table} tt on dw.id = tt.word_id"""


class UserListGrammarRule:
    user_list = models.ForeignKey(UserList, on_delete=models.CASCADE)
    user_grammar_rule = models.ForeignKey(UserGrammarRule, on_delete=models.CASCADE)


class UserListWord:
    user_list = models.ForeignKey(UserList, on_delete=models.CASCADE)
    user_word = models.ForeignKey(UserWord, on_delete=models.CASCADE)


class Goal(DetailedModel):
    user_list = models.ForeignKey(UserList, on_delete=models.CASCADE, null=True)
    parent = models.ForeignKey("self", on_delete=models.CASCADE, null=True)
