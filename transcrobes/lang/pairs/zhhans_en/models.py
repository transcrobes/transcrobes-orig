# -*- coding: utf-8 -*-

from django.db import models

from enrich.models import JsonTranslation


class ABCLookup(JsonTranslation):
    pass

class CCCLookup(JsonTranslation):
    pass

