# -*- coding: utf-8 -*-

from abc import ABC, abstractmethod
import logging
import requests
import json
from django.conf import settings


logger = logging.getLogger(__name__)


class NLPProvider(ABC):
    @abstractmethod
    def parse(self, input):
        pass


class OpenNLPProvider(NLPProvider):
    def parse(self, text):
        logger.debug('Starting OpenNLPProvider parse of: {}'.format(text))

        params = {'properties': settings.OPENNLP_PARSE_PROPERTIES}
        r = requests.post(settings.OPENNLP_URL, data=text.encode("utf-8"), params=params)
        r.raise_for_status()

        logger.debug("Got the following back from OpenNLP: {}".format(r.text))
        model = json.loads(r.text)

        logger.debug("Finished getting model from corenlp")
        return model
