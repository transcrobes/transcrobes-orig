# -*- coding: utf-8 -*-

import base64
import json

# TODO: need to migrate to JWT
def get_credentials(request):
    auth_header = request.META.get('HTTP_AUTHORIZATION')
    if auth_header:
        encoded_credentials = auth_header.split(' ')[1]  # Removes "Basic " to isolate credentials
        decoded_credentials = base64.b64decode(encoded_credentials).decode("utf-8").split(':')
        username = decoded_credentials[0]
        password = decoded_credentials[1]
        return username, password
    elif request.method == "POST":
        post_data = json.loads(request.body)
        username = post_data['username']
        password = post_data['password']
        return username, password
    else:
        return None, None
