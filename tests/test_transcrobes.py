# -*- coding: utf-8 -*-
import base64

from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from vcr_unittest import VCRMixin


class AuthMixin(VCRMixin):
    databases = "__all__"
    USERNAME = "a_username"
    PASSWORD = "a_pass_word"

    ##
    ## Plumbing methods
    ##

    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(username=self.USERNAME, password=self.PASSWORD)

    def tearDown(self):
        self.user.delete()

    ##
    ## Methods of auth
    ##
    def test_basic_authentication(self):
        # basic, session and token should all work, non authenticated or incorrectly authenticated should all fail

        url = reverse("word_definitions")
        data = {"data": "好"}
        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        self.client.credentials(
            HTTP_AUTHORIZATION=b"Basic " + base64.b64encode(f"{self.USERNAME}:{self.PASSWORD}".encode())
        )

        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_jwt_authentication(self):
        url = reverse("word_definitions")
        data = {"data": "好"}
        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + "abc")
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        token_url = reverse("token_obtain_pair")
        auth = {"username": self.USERNAME, "password": self.PASSWORD}
        response = self.client.post(token_url, auth)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertTrue("access" in response.data)
        token = response.data["access"]

        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + token)
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_session_authentication(self):
        url = reverse("word_definitions")
        data = {"data": "好"}
        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.client.login(username="unknown_user", password="unknown_password")

        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        self.client.login(username=self.USERNAME, password=self.PASSWORD)
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class AuthTests(AuthMixin, APITestCase):
    pass


# # FIXME: these definitely need doing !!!
# class UtilsTests(TestCase):
#     ##
#     ## Plumbing methods
#     ##
#
#     def setUp(self):
#         pass
#
#     ##
#     ## Tests for helper methods
#     ##
#     def test_default_definition(self):
#         pass
#
#     def test_note_format(self):
#         pass
#
#     def test_get_username_lang_pair(self):
#         pass
