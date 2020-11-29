# -*- coding: utf-8 -*-

from django import forms


class CreateListForm(forms.Form):
    your_name = forms.CharField(label="Your name", max_length=100)
