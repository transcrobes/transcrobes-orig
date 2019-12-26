# -*- coding: utf-8 -*-
import logging

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import connection
from django.http import JsonResponse
from django.urls import reverse
from django.views.generic import TemplateView
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from data.utils import update_user_rules, update_user_words
from enrich.data import managers
from utils import default_definition

logger = logging.getLogger(__name__)

# PROD

# Ideas for improvements
# - instead of just recording the word as seen/checked, add POS for the actual tokens in the text
@permission_classes((IsAuthenticated,))
@api_view(["POST", "OPTIONS"])
def update_model(request):
    if request.method == "POST":
        voc = request.data["vocab"]
        rlz = request.data["rules"]
        update_user_words(voc, request.user)
        update_user_rules(rlz, request.user)

    data = {"status": "success"}
    response = JsonResponse(data)
    response["Access-Control-Allow-Origin"] = "*"
    response["Access-Control-Allow-Methods"] = "POST, OPTIONS"
    response["Access-Control-Allow-Headers"] = "X-Requested-With, Content-Type, Authorization"
    return response


# END PROD

# BOOTSTRAP INVESTIGATIONS


class VocabList(LoginRequiredMixin, TemplateView):
    template_name = "data/vocab_list.html"
    login_url = "/accounts/login/"

    def vocab_list(self, _list_type="SUB", start=0, window_size=100):
        username = self.request.user.username
        lang_pair = self.request.user.transcrober.lang_pair()
        manager = managers.get(lang_pair)
        if not manager:
            raise Exception(f"Server does not support language pair {lang_pair}")

        # TODO: the following
        # get list of words from list X that are not in username.notes with definitions from bingapilookup
        # ordered by list X

        # FIXME: sql injection fun!!! ???
        # FIXME: this should allow for re-running the tool!
        sql = f"""
        select source_text from enrichers_zh_subtlexlookup sub
            left join {username}.notes n on sub.source_text = n.word where n.word is null
        order by sub.id
        limit %(window_size)s
        offset %(start)s
        """

        page_words = None
        with connection.cursor() as cursor:
            cursor.execute(sql, {"window_size": window_size, "start": start})
            page_words = cursor.fetchall()

        data = []
        for pw in page_words:
            w = pw[0]
            data.append(default_definition(manager, w))
        return data

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["data"] = self.vocab_list()
        context["vocab"] = {x["Simplified"]: [0, 0] for x in context["data"]}
        context["post_ep"] = reverse("add_words")

        return context
