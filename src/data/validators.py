# -*- coding: utf-8 -*-

from django.conf import settings
from django.core.exceptions import ValidationError


def validate_file_size(value):
    if value.size > settings.IMPORT_MAX_UPLOAD_SIZE_KB * 1024:  # value.size is in bytes
        raise ValidationError(
            f"The maximum file size that can be uploaded is {settings.IMPORT_MAX_UPLOAD_SIZE_KB}KB", code="filesize"
        )
    return value
