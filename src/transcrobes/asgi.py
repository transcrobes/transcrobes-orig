# -*- coding: utf-8 -*-

import os

from django.core.asgi import get_asgi_application
from starlette.websockets import WebSocketDisconnect

from data.asgi import TranscrobesGraphQL

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "transcrobes.settings")

django_application = get_asgi_application()


async def application(scope, receive, send):
    if scope["type"] == "http":
        await django_application(scope, receive, send)
    elif scope["type"] == "websocket":
        try:
            import data.schema  # noqa  # pylint: disable=C0415

            graphql_app = TranscrobesGraphQL(data.schema.schema, keep_alive=True, keep_alive_interval=5)
            await graphql_app(scope, receive, send)
        except WebSocketDisconnect:
            pass
    else:
        raise NotImplementedError(f"Unknown scope type {scope['type']}")
