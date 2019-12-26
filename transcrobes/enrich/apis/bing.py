# -*- coding: utf-8 -*-

import json
import logging
import uuid
from abc import ABC

import requests

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
