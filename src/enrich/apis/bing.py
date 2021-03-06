# -*- coding: utf-8 -*-

import json
import logging
import uuid
from abc import ABC

import aiohttp
import requests
from aiohttp_retry import ExponentialRetry, RetryClient

URL_SCHEME = "https://"

logger = logging.getLogger(__name__)


class BingAPI(ABC):
    def __init__(self, config):
        self.from_lang = config["from"]
        self.to_lang = config["to"]
        self._api_key = config["api_key"]
        self._api_host = config["api_host"]

    def default_params(self):
        return {
            "api-version": "3.0",
            "from": self.from_lang,
            "to": self.to_lang,
        }

    # private methods
    @staticmethod
    def _request_json(text):
        requestBody = [{"Text": text}]
        return json.dumps(requestBody, ensure_ascii=False)

    # protected methods
    def _ask_bing_api(self, content, path, params):
        req_json = self._request_json(content)
        logger.debug("Looking up '%s' in Bing using json: %s", content, req_json)
        headers = {  # leave this here for the moment - we may want to log the trace id properly
            "Ocp-Apim-Subscription-Key": self._api_key,
            "Content-type": "application/json",
            "X-ClientTraceId": str(uuid.uuid4()),
        }
        r = requests.post(
            "{}{}{}".format(URL_SCHEME, self._api_host, path),
            data=req_json.encode("utf-8"),
            params=params,
            headers=headers,
        )
        logger.debug("Received '%s' back from Bing", r.text)
        r.raise_for_status()

        return r.text

    async def _aask_bing_api_orig(self, content, path, params, max_attempts=5, max_wait_between_attempts=30):
        req_json = self._request_json(content)
        logger.debug("Async looking up '%s' in Bing using json: %s", content, req_json[:100])

        headers = {  # leave this here for the moment - we may want to log the trace id properly
            "Ocp-Apim-Subscription-Key": self._api_key,
            "Content-type": "application/json",
            "X-ClientTraceId": str(uuid.uuid4()),
        }
        ## the max_timeout option is horribly named, it is the wait between attempts, not timeout at all...
        retry_options = ExponentialRetry(attempts=max_attempts, max_timeout=max_wait_between_attempts)
        async with RetryClient(raise_for_status=False, retry_options=retry_options) as client:
            try:
                async with client.post(
                    "{}{}{}".format(URL_SCHEME, self._api_host, path),
                    data=req_json.encode("utf-8"),
                    params=params,
                    headers=headers,
                ) as response:
                    response.raise_for_status()
                    text = await response.text()
                    logger.debug("Received '%s' back from Bing", text[:100])
                    return text
            except aiohttp.client_exceptions.ClientConnectorError:
                logger.error("Failure to send to Bing API: %s", content)
                raise

    async def _aask_bing_api(self, content, path, params, max_attempts=5, max_wait_between_attempts=30):
        req_json = self._request_json(content)
        logger.debug("Async looking up '%s' in Bing using json: %s", content, req_json[:100])

        headers = {  # leave this here for the moment - we may want to log the trace id properly
            "Ocp-Apim-Subscription-Key": self._api_key,
            "Content-type": "application/json",
            "X-ClientTraceId": str(uuid.uuid4()),
        }
        ## the max_timeout option is horribly named, it is the wait between attempts, not timeout at all...
        retry_options = ExponentialRetry(attempts=max_attempts, max_timeout=max_wait_between_attempts)
        async with RetryClient(
            raise_for_status=True,
            retry_options=retry_options,
            connector=aiohttp.TCPConnector(enable_cleanup_closed=True, force_close=True),
        ) as client:
            try:
                async with client.post(
                    f"{URL_SCHEME}{self._api_host}{path}", data=req_json.encode("utf-8"), params=params, headers=headers
                ) as response:
                    text = await response.text()
                    logger.debug("Received '%s' back from Bing", text[:100])
                    return text
            except aiohttp.client_exceptions.ClientConnectorError:
                logger.error("Failure to send to Bing API: %s", content)
                raise
