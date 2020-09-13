# -*- coding: utf-8 -*-
from django.contrib.auth.models import User
from rest_framework import serializers

from data.models import Survey, UserSurvey


class SurveySerialiser(serializers.HyperlinkedModelSerializer):
    users = serializers.HyperlinkedRelatedField(many=True, view_name="user-detail", read_only=True)

    class Meta:
        model = Survey
        fields = ["url", "id", "survey_json", "users"]


class UserSurveySerialiser(serializers.HyperlinkedModelSerializer):
    user = serializers.ReadOnlyField(source="user.username")

    class Meta:
        model = UserSurvey
        fields = ["url", "id", "user", "survey", "data"]


class UserSerialiser(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = User
        fields = ["url", "id", "username"]
