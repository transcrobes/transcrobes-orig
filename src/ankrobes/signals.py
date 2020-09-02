# -*- coding: utf-8 -*-

from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Transcrober


@receiver(post_save, sender=User)  # pylint: disable=W0613
def update_profile_signal(sender, instance, created, **kwargs):  # pylint: disable=W0613
    if created:
        t = Transcrober()
        t.user = instance
        t.save()
        t.init_collection()
