# -*- coding: utf-8 -*-
import logging

from django.core.management.base import BaseCommand

from enrich.cache import regenerate_definitions_jsons_multi

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = """Regenerate the JSON definitions caches"""

    def add_arguments(self, parser):
        parser.add_argument("--fakelimit", nargs="?", type=int)

    def handle(self, *args, **options):
        logger.info("Starting to regenerate definitions caches")
        if options.get("fakelimit"):
            print("Generating a fake limited dataset with a limit of ", options.get("fakelimit"))
        regenerate_definitions_jsons_multi(options.get("fakelimit") or 0)
        logger.info("Finished regenerating definitions caches")
