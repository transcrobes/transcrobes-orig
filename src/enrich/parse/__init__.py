# -*- coding: utf-8 -*-

import json
import logging
import socket
from abc import ABC, abstractmethod

import requests
import xmltodict

logger = logging.getLogger(__name__)


class ParseProvider(ABC):
    def __init__(self, config):
        self._config = config

    @abstractmethod
    def parse(self, _input):
        """
        Take input, parse (or get done externally) and send back marked up in json format
        """


"""
TODO: currently unused, as we want proper word offsets and using the main provider
means we can have identical config for the supported languages. Left here in case
we decide using postagger directly is worth the hassle (for significantly reduced
memory usage
"""


class SocketCoreNLPProvider(ParseProvider):
    def parse(self, text):
        logger.debug("Starting SocketCoreNLPProvider parse of: %s", text)

        clientsocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        clientsocket.connect((self._config["host"], int(self._config["port"])))
        clientsocket.send(str.encode(text + "\n"))
        ret = clientsocket.recv(16384).decode()
        buf = ret
        while True:
            if len(ret) > 0:
                ret = clientsocket.recv(16384).decode()
                buf = buf + ret  # clientsocket.recv(16384).decode()
            else:
                break
        doc = f"<doc>{buf}</doc>"

        outmodel = {"sentences": []}
        sInd = 0
        # TODO: we should either just iterate on the xml directly or tell xmltodict what
        # structure to use - double-handling is stupid
        m = xmltodict.parse(doc, dict_constructor=dict, attr_prefix="", cdata_key="originalText")
        for s in m["doc"]["sentence"]:
            wInd = 1
            sentence = {"index": sInd, "tokens": []}
            sInd += 1
            for w in s["word"]:
                sentence["tokens"].append(
                    {"index": wInd, "word": w["lemma"], "originalText": w["originalText"], "pos": w["pos"]}
                )
                wInd += 1

            outmodel["sentences"].append(sentence)

        return outmodel


class HTTPCoreNLPProvider(ParseProvider):
    def parse(self, text):
        logger.debug("Starting HTTPCoreNLPProvider parse of: %s", text)

        params = {"properties": self._config["params"]}

        r = requests.post(self._config["base_url"], data=text.encode("utf-8"), params=params)
        r.raise_for_status()

        logger.debug("Got the following back from CoreNLP via http: %s", r.text)
        model = json.loads(r.text)

        logger.debug("Finished getting model from CoreNLP via http")
        return model
