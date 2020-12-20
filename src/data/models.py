# -*- coding: utf-8 -*-
import csv
import io
import json
import logging
import os

from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.db import connection, models
from django.urls import reverse
from django.utils import timezone
from django_extensions.db.models import ActivatorModel, TimeStampedModel, TitleSlugDescriptionModel
from upload_validator import FileTypeValidator

from ankrobes import Ankrobes
from enrich.models import BingAPILookup, BingAPITranslation
from utils import default_definition  # , SIMPLIFIED_UTF8_ORD_MIN, SIMPLIFIED_UTF8_ORD_MAX

from .validators import validate_file_size

SIMPLIFIED_UTF8_ORD_MIN = 22909
SIMPLIFIED_UTF8_ORD_MAX = 40869

logger = logging.getLogger(__name__)


class DetailedModel(ActivatorModel, TimeStampedModel, TitleSlugDescriptionModel):
    def __str__(self):
        return f"{self.title}"

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

    process_type = models.IntegerField(choices=PROCESS_TYPE, default=VOCABULARY_ONLY, help_text="What items to extract")
    user = models.ForeignKey(User, on_delete=models.CASCADE, help_text="Import owner")
    import_file = models.FileField(
        upload_to=user_directory_path,
        validators=[
            FileTypeValidator(allowed_types=["text/plain", "text/csv", "application/csv"]),
            FileExtensionValidator(allowed_extensions=["txt", "csv"]),
            validate_file_size,
        ],
        help_text="File to import",
    )

    # TODO: think about alerting if the object modification time is too old and processed = null
    processed = models.BooleanField(
        default=False, null=True, help_text="Import status"
    )  # False = new, null = processing, True = processed

    # TODO: maybe use a JSONField? It's JSON but we likely don't need the overhead in the db
    analysis = models.TextField(null=True)

    # shared, can be seen by others, and used as a template for creating their own versions
    shared = models.BooleanField(default=False, help_text="Allow others to see and use this import?")

    def processing_status(self):
        if self.processed:
            return "Processed"

        if self.processed is None:
            return "Processing"

        return "Waiting"

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
    ABSOLUTE_FREQUENCY = 0
    IMPORT_FREQUENCY = 1
    # A mix of the two? With a weight?
    ORDER_BY_CHOICES = [
        (ABSOLUTE_FREQUENCY, "Absolute Frequency"),
        (IMPORT_FREQUENCY, "Frequency in import"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    the_import = models.ForeignKey(Import, on_delete=models.CASCADE, help_text="The import to create the list from")

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
    processed = models.BooleanField(default=False, null=True)  # False = new, null = processing, True = processed

    # actions
    add_notes = models.BooleanField(default=False, help_text="Should Anki notes be added for each word?")
    notes_are_known = models.BooleanField(default=False, help_text="Should the notes added be set to already known?")

    def get_absolute_url(self):
        return reverse("list_detail", args=[str(self.id)])

    def processing_status(self):
        if self.processed:
            return "Processed"

        if self.processed is None:
            return "Processing"

        return "Waiting"

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
                # our reference values
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

            if self.only_dictionary_words:
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
            for word_id in cur.fetchall():
                new_userwords.append(UserWord(user=self.user, word_id=word_id[0]))
                new_userlistwords.append(UserListWord(user_list=self, word_id=word_id[0]))

            # bulk create using objects
            # TODO: if this is slow due to ignore_conflicts, maybe update with the id
            # before doing this and only select those without an id
            UserWord.objects.bulk_create(new_userwords, ignore_conflicts=True)
            UserListWord.objects.bulk_create(new_userlistwords, ignore_conflicts=True)  # can there be conflicts?

            logger.info(f"Added {len(new_userlistwords)} list words for user_list_{self.id} for {self.user.username}")
            if self.add_notes:
                with Ankrobes(self.user.username) as userdb:
                    for ulword in UserListWord.objects.filter(user_list=self):
                        # TODO: decide how to best deal with when to next review
                        # at least this should maybe have a random date set
                        review_in = 7 if self.notes_are_known else 0

                        word = ulword.word.source_text

                        defin = default_definition(manager, word)
                        if not userdb.set_word_known(
                            simplified=defin["Simplified"],
                            pinyin=defin["Pinyin"],
                            meanings=[defin["Meaning"]],
                            tags=[f"user_list_{self.id}"],  # FIXME: should this add tags, or overwrite?
                            review_in=review_in,
                        ):
                            logger.error(
                                f"Error setting the word_known status for {word} for user {self.user.username}"
                            )
                            raise Exception(f"Error updating the user database for {self.user.username}")

                    logger.info(f"Set {len(new_userlistwords)} notes for user_list_{self.id} for {self.user.username}")

                    # FIXME: remove nasty hack
                    self.user.transcrober.refresh_vocabulary()

            cur.execute(f"DROP TABLE {temp_table}")
            self.processed = True
            self.save()


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

    # def get_progress_percent(self):
    #     known_words, all_words = self.get_progress()
    #     # return f"{(known_words*100/all_words):.0f}" if all_words else ""
    #     return (known_words*100/all_words) if all_words else None

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
