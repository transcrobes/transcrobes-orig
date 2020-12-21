import json
from typing import Any

from django.conf import settings
from kafka import KafkaProducer

USER_STATS_MODE_IGNORE = -1
GLOSSING_MODE_UNMODIFIED = 0
GLOSSING_MODE_SEGMENT_ONLY = 2  # word-segmented
GLOSSING_MODE_L2_SIMPLIFIED = 4  # Simpler synonym, not yet implemented
GLOSSING_MODE_TRANSLITERATION = 6  # Pinyin
GLOSSING_MODE_L1 = 8  # English

USER_GLOSSING_MODE = [
    (GLOSSING_MODE_UNMODIFIED, "Unmodified text"),
    (GLOSSING_MODE_L2_SIMPLIFIED, "Simpler words"),
    (GLOSSING_MODE_TRANSLITERATION, "Transliteration"),
    (GLOSSING_MODE_L1, "Native language"),
]

USER_STATS_MODE = [
    (USER_STATS_MODE_IGNORE, "Ignore"),
    (GLOSSING_MODE_SEGMENT_ONLY, "Segmentation only"),
] + USER_GLOSSING_MODE

KAFKA_PRODUCER: KafkaProducer


def _kafka_producer() -> KafkaProducer:
    global KAFKA_PRODUCER  # pylint: disable=W0603
    KAFKA_PRODUCER = KafkaProducer(
        bootstrap_servers=[settings.KAFKA_BROKER], value_serializer=lambda m: json.dumps(m).encode("ascii")
    )
    return KAFKA_PRODUCER


def __getattr__(name: str) -> Any:
    if name == "KAFKA_PRODUCER":
        return _kafka_producer()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
