import json
from typing import Any

from django.conf import settings
from kafka import KafkaProducer

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
