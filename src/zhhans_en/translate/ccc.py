# -*- coding: utf-8 -*-
import logging
import os
import re

from enrich.data import PersistenceProvider
from enrich.translate import Translator
from enrichers.zhhans import ZH_TB_POS_TO_SIMPLE_POS
from ndutils import lemma
from zhhans_en.models import CCCLookup
from zhhans_en.translate import decode_pinyin

logger = logging.getLogger(__name__)


class ZHHANS_EN_CCCedictTranslator(PersistenceProvider, Translator):
    SHORT_NAME = "ccc"
    model_type = CCCLookup

    # override PersistenceProvider
    def _load(self):
        """
        Loads from an unmodified CC-Cedict file
        We basically just straight load the file, though we ignore the Traditional characters
        """
        logger.info("Populating cedict")
        dico = {}

        if not os.path.exists(self._config["path"]):
            logger.error(f"Should have loaded the file {self._config['path']} but it doesn't exist")
            return dico

        with open(self._config["path"], "r") as data_file:
            for line in data_file:
                line = line.strip()
                if line.startswith("#"):
                    continue
                regex = r"^(\S+)\s+(\S+)\s+(\[[^]]+\])\s+(\/.*\/)$"

                match = re.search(regex, line)
                if not match:
                    continue
                if not match.group(2) in dico:
                    dico[match.group(2)] = []

                dico[match.group(2)].append(
                    {"pinyin": match.group(3), "definitions": match.group(4).strip("/").split("/")}
                )

        logger.info("Finished populating cedict, there are %s entries", len(list(dico.keys())))
        return dico

    # override Translator
    @staticmethod
    def name():
        return "ccc"

    @staticmethod
    def _decode_pinyin(s):
        # TODO: don't use the generic method here
        return decode_pinyin(s)

    def _def_from_entry(self, token, cccl):
        std_format = {}
        if cccl:
            logger.debug("'%s' is in cccedict cache", lemma(token))
            for cc in cccl:
                logger.debug("Iterating on '%s''s different forms in cccedict cache", lemma(token))
                for defin in cc["definitions"]:
                    logger.debug("Iterating on '%s''s different definitions in cccedict cache", lemma(token))
                    logger.debug("Checking for POS hint for '%s' in cccedict", lemma(token))
                    token_pos = ZH_TB_POS_TO_SIMPLE_POS[token["pos"]]

                    if defin.startswith("to "):
                        defin_pos = "VERB"
                    elif defin.startswith("a "):
                        defin_pos = "NOUN"
                    else:
                        defin_pos = "OTHER"

                    if defin_pos not in std_format:
                        std_format[defin_pos] = []

                    confidence = 0

                    if (token_pos == "VERB" and defin_pos == "VERB") or (token_pos == "NOUN" and defin_pos == "NOUN"):
                        confidence = 0.01

                    defie = {
                        "upos": defin_pos,
                        "opos": defin_pos,
                        "normalizedTarget": defin,
                        "confidence": confidence,
                        "trans_provider": "CEDICT",
                    }
                    defie["pinyin"] = self._decode_pinyin(cc["pinyin"])
                    std_format[defin_pos].append(defie)

        logger.debug("Finishing looking up '%s' in cccedict", lemma(token))
        return std_format

    async def aget_standardised_defs(self, token):
        return self._def_from_entry(token, await self._aget_def(lemma(token)))

    # TODO: investigate git@github.com:wuliang/CedictPlus.git - it has POS. It also hasn't been updated in 6 years...
    # override Translator
    def get_standardised_defs(self, token):
        return self._def_from_entry(token, self._get_def(lemma(token)))

    # override Translator
    def get_standardised_fallback_defs(self, token):
        # TODO: do something better than this!
        return self.get_standardised_defs(token)

    # override Translator
    def synonyms(self, token, std_pos, max_synonyms=5):
        raise NotImplementedError

    # override Translator
    async def sound_for(self, token):
        cccl = await self._aget_def(lemma(token))
        if cccl:
            for cc in cccl:
                logger.debug("Iterating on '%s''s different forms in cccedict cache", lemma(token))
                for sound in cc["pinyin"]:
                    if sound:
                        return self._decode_pinyin(sound)
        return ""
