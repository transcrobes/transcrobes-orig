# -*- coding: utf-8 -*-

from django.contrib import admin

from .models import GrammarRule, Source, UserGrammarRule

admin.site.register(Source)
admin.site.register(GrammarRule)
admin.site.register(UserGrammarRule)
