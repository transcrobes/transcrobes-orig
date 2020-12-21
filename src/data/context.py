# -*- coding: utf-8 -*-

from dataclasses import dataclass

from broadcaster import Broadcast
from django.conf import settings
from django.http import HttpRequest

broadcast = None


async def get_broadcast():
    global broadcast  # pylint: disable=W0603

    if not broadcast:
        if settings.BROACASTER_MESSAGING_LAYER == "postgres":  # pylint: disable=R1720
            raise NotImplementedError("PGPool has to be at least 4.2.3 before this can be activated")
            # dbinfo = connection.settings_dict
            # host = f"{dbinfo.get('HOST')}:{dbinfo.get('PORT')}" if dbinfo.get("PORT") else dbinfo.get("HOST")
            # dsnstr = f"postgresql://{dbinfo.get('USER')}:{dbinfo.get('PASSWORD')}@{host}/{dbinfo.get('NAME')}"
            # broadcast = Broadcast(dsnstr)
        elif settings.BROACASTER_MESSAGING_LAYER == "kafka":
            broadcast = Broadcast(f"kafka://{settings.KAFKA_BROKER}")
        else:
            broadcast = Broadcast("memory://")

        await broadcast.connect()

    return broadcast


@dataclass
class Context:
    broadcast: Broadcast
    request: HttpRequest
