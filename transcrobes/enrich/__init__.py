# -*- coding: utf-8 -*-

import os
import sys

# This way of doing things is modelled on the original ankisyncd
# there may well be a better way!
sys.path.insert(0, "/usr/share/anki")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "anki-bundled"))

default_app_config = 'enrich.apps.EnrichConfig'
