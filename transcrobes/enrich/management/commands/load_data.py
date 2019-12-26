# -*- coding: utf-8 -*-
import os

from django.core.management.base import BaseCommand, CommandError

from en_zhhans.translate.abc import EN_ZHHANS_ABCDictTranslator
from enrichers.en.metadata.subtlex import EN_SubtlexMetadata
from enrichers.en.transliterate.cmu import CMU_EN_Transliterator
from enrichers.zhhans.metadata.hsk import ZH_HSKMetadata
from enrichers.zhhans.metadata.subtlex import ZH_SubtlexMetadata
from zhhans_en.translate.abc import ZHHANS_EN_ABCDictTranslator
from zhhans_en.translate.ccc import ZHHANS_EN_CCCedictTranslator

DATA_PROVIDERS = {
    "en_zh_abc_dict": EN_ZHHANS_ABCDictTranslator,
    "zh_en_abc_dict": ZHHANS_EN_ABCDictTranslator,
    "zh_en_cedict": ZHHANS_EN_CCCedictTranslator,
    "en_cmu_dict": CMU_EN_Transliterator,
    "zh_hsk_lists": ZH_HSKMetadata,
    "zh_subtlex_freq": ZH_SubtlexMetadata,
    "en_subtlex_freq": EN_SubtlexMetadata,
}


class Command(BaseCommand):
    help = """Allows (re)loading of data sources to the DB. This goes through the configured settings,
    finds the files corresponding to the data_providers specified and loads to the database"""

    def add_arguments(self, parser):
        parser.add_argument(
            "-d",
            "--data_provider",
            action="append",
            nargs="+",
            choices=list(DATA_PROVIDERS.keys()),
            help="Default: None. Specify a dataprovider to load, can be specified "
            "multiple times to (re)load several",
        )
        parser.add_argument(
            "-a",
            "--all",
            default=False,
            action="store_true",
            help="Default: False. Load all datafiles (overrides --data_provider)",
        )
        parser.add_argument(
            "-f",
            "--force_reload",
            default=False,
            action="store_true",
            help="Default: False. Force reloading, even if there is already a " "value in the DB for an entry",
        )

    def handle(self, *args, **options):

        all_data = options["all"]
        data_provider = options["data_provider"]
        force_reload = options["force_reload"]
        to_load = list([x] for x, _y in DATA_PROVIDERS.items()) if all_data else data_provider

        if not to_load:
            raise CommandError("You must either specify --all or provider a --data_provider")

        for prov in to_load:
            dp = prov[0]

            path = os.getenv(f"TRANSCROBES_{dp.upper()}_PATH")
            self.stdout.write(f"Loading data to DB for {dp} from path {path}")
            loader = DATA_PROVIDERS[dp]({"path": path, "inmem": True})
            loader.load_to_db(loader.dico, force_reload)
            self.stdout.write(f"Loaded data to DB for {dp} from path {path}")

        self.stdout.write(f'Finished loading providers to DB for: {", ".join([x[0] for x in to_load])}')
