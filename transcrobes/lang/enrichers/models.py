# -*- coding: utf-8 -*-

from django.db import models

from enrich.models import JsonTranslation

# For en
# TODO: move this out into an independent app somehow
class EN_CMULookup(JsonTranslation):
    pass

class EN_SubtlexLookup(JsonTranslation):
    pass

# For zh-hans
# TODO: move this out into an independent app somehow
class ZH_HSKLookup(JsonTranslation):
    pass

class ZH_SubtlexLookup(JsonTranslation):
    pass
