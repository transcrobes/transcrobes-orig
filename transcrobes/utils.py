# -*- coding: utf-8 -*-

import base64

# TODO: need to migrate to JWT
def get_credentials(request):
    auth_header = request.META.get('HTTP_AUTHORIZATION')
    if auth_header:  # prefer Basic Auth if present
        encoded_credentials = auth_header.split(' ')[1]  # Removes "Basic " to isolate credentials
        decoded_credentials = base64.b64decode(encoded_credentials).decode("utf-8").split(':')
        return decoded_credentials[0], decoded_credentials[1]
    else:
        return None, None

