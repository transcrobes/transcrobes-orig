# -*- coding: utf-8 -*-

import json
import logging
from abc import ABC, abstractmethod
from urllib.parse import quote

import requests
from aiohttp_retry import ExponentialRetry, RetryClient

logger = logging.getLogger(__name__)


class ParseProvider(ABC):
    def __init__(self, config):
        self._config = config

    @abstractmethod
    def parse(self, _input, _provider_parameters=None):
        """
        Take input, parse (or get done externally) and send back marked up in json format
        """


class HTTPCoreNLPProvider(ParseProvider):
    # FIXME: the sync version of `aparse`, it should probably disappear
    def parse(self, text, provider_parameters=None):
        logger.debug("Starting HTTPCoreNLPProvider parse of: %s", text)

        params = {"properties": provider_parameters or self._config["params"]}

        r = requests.post(self._config["base_url"], data=quote(text), params=params)
        r.raise_for_status()

        logger.debug("Got the following back from CoreNLP via http: %s", r.text)
        model = json.loads(r.text)

        logger.debug("Finished getting model from CoreNLP via http")
        return model

    async def aparse(self, text, provider_parameters=None, max_attempts=5, max_wait_between_attempts=300):
        ## the max_timeout option is horribly named, it is the wait between attempts, not timeout at all...
        retry_options = ExponentialRetry(attempts=max_attempts, max_timeout=max_wait_between_attempts)
        async with RetryClient(raise_for_status=False, retry_options=retry_options) as client:
            logger.debug("Starting HTTPCoreNLPProvider aparse of: %s", text)
            params = {"properties": provider_parameters or self._config["params"]}
            async with client.post(self._config["base_url"], data=text, params=params) as response:
                response.raise_for_status()
                logger.debug("Finished getting model from CoreNLP via http")
                return await response.json()
