# -*- coding: utf-8 -*-
import logging

from django.core.management.base import BaseCommand

from enrich.cache import regenerate_character_jsons_multi, regenerate_definitions_jsons_multi

logger = logging.getLogger(__name__)

DATA_PROVIDERS = ["definitions", "characters", "both"]


class Command(BaseCommand):
    help = """Regenerate the JSON definitions caches"""

    def add_arguments(self, parser):
        parser.add_argument("--fakelimit", nargs="?", type=int)
        parser.add_argument(
            "-d",
            "--data_provider",
            nargs="?",
            default="both",
            choices=DATA_PROVIDERS,
            help="Default: Both. Specify a dataprovider to load: 'definitions', 'characters' or 'both'",
        )

    def handle(self, *args, **options):
        logger.info("Starting to regenerate definitions caches")
        if options.get("fakelimit"):
            print("Generating a fake limited dataset with a limit of ", options.get("fakelimit"))
        if options.get("data_provider") in ["both", "definitions"]:
            regenerate_definitions_jsons_multi(options.get("fakelimit") or 0)
        if options.get("data_provider") in ["both", "characters"]:
            regenerate_character_jsons_multi(options.get("fakelimit") or 0)
        logger.info("Finished regenerating caches")
