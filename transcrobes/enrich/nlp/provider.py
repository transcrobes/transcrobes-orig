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


class CoreNLPProvider(NLPProvider):
    def parse(self, text):
        logger.debug('Starting CoreNLPProvider parse of: {}'.format(text))

        params = {'properties': settings.CORENLP_PARSE_PROPERTIES}
        r = requests.post(settings.CORENLP_URL, data=text.encode("utf-8"), params=params)
        r.raise_for_status()

        logger.debug("Got the following back from CoreNLP: {}".format(r.text))
        model = json.loads(r.text)

        logger.debug("Finished getting model from CoreNLP")
        return model
