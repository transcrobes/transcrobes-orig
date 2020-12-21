# -*- coding: utf-8 -*-

from django.forms import ModelForm

from data.models import Transcrober


class TranscroberForm(ModelForm):
    class Meta:
        model = Transcrober
        fields = ["default_glossing", "reading_mode", "font_size_percent"]
