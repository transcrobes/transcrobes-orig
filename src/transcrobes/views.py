# -*- coding: utf-8 -*-

import os
import socket

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


@api_view(["GET", "POST"])
@permission_classes((AllowAny,))
def hello(_request):
    return Response("Hello, World!")


@api_view(["GET"])
def pod_details(_request):
    return Response(
        {
            "socket_fqdn": socket.getfqdn(),
            "TRANSCROBES_NODE_NAME": os.getenv("TRANSCROBES_NODE_NAME"),
            "TRANSCROBES_POD_IP": os.getenv("TRANSCROBES_POD_IP"),
            "TRANSCROBES_HOST_IP": os.getenv("TRANSCROBES_HOST_IP"),
            "TRANSCROBES_POD_NAME": os.getenv("TRANSCROBES_POD_NAME"),
            "TRANSCROBES_POD_NAMESPACE": os.getenv("TRANSCROBES_POD_NAMESPACE"),
        }
    )
