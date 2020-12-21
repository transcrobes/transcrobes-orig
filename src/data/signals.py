# -*- coding: utf-8 -*-
import logging

from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Transcrober

logger = logging.getLogger(__name__)


@receiver(post_save, sender=User)  # pylint: disable=W0613
def update_profile_signal(sender, instance, created, **kwargs):  # pylint: disable=W0613
    if created or not instance.transcrober:
        logging.debug("Creating new Transcrober for user %s", instance)
        t = Transcrober()
        t.user = instance
        t.save()
        logging.debug("Successfully created new Transcrober for user %s", instance)
