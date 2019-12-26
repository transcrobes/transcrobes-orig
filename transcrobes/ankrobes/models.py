# -*- coding: utf-8 -*-

from django.contrib.auth.models import User
from django.db import models


class Transcrober(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    # TODO: this should probably be a OneToMany, so we can have users
    # who use the system for more than one language. KISS for the moment
    from_lang = models.CharField(max_length=20, default="zh-Hans")  # 20 is probably overkill
    to_lang = models.CharField(max_length=20, default="en")  # 20 is probably overkill

    def lang_pair(self):
        return f"{self.from_lang}:{self.to_lang}"
