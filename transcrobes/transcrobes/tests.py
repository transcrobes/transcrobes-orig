# -*- coding: utf-8 -*-

import json
import logging
import base64
import time

from django.contrib.auth.models import AnonymousUser, User
from django.test import TestCase, RequestFactory, Client
from django.core.cache import cache

from .views import authget
from utils import get_credentials

class AuthTests(TestCase):
    ##
    ## Plumbing methods
    ##

    def setUp(self):
        self.user = User.objects.create_user(
            username='toto', email='toto@transcrob.es', password='top_secret')
        self.client = Client()
        self.factory = RequestFactory()

    # def tearDown(self):
    #     raise NotImplementedError

    ##
    ## Tests for authentication method `authget`
    ##

    def test_valid_user_succeeds(self):
        cache.delete(self.user.username)  # ensure a previous attempt hasn't poisoned the cache
        credentials = base64.b64encode(f'{self.user.username}:top_secret'.encode('utf-8')).decode("utf-8")

        self.client.defaults['HTTP_AUTHORIZATION'] = 'Basic ' + credentials
        resp = self.client.get('/authget')
        self.assertEqual(resp.status_code, 200)

    def test_invalid_user_fails(self):
        cache.delete(self.user.username)  # ensure a previous attempt hasn't poisoned the cache
        credentials = base64.b64encode(f'{self.user.username}:not_so_top_secret'.encode('utf-8')).decode("utf-8")
        self.client.defaults['HTTP_AUTHORIZATION'] = 'Basic ' + credentials
        resp = self.client.get('/authget')
        self.assertEqual(resp.status_code, 401)

    def test_invalid_request_fails(self):
        cache.delete(self.user.username)  # ensure a previous attempt hasn't poisoned the cache
        credentials = base64.b64encode(f'{self.user.username}:'.encode('utf-8')).decode("utf-8")
        self.client.defaults['HTTP_AUTHORIZATION'] = 'Basic ' + credentials
        resp = self.client.get('/authget')
        self.assertEqual(resp.status_code, 401)

    def test_invalid_request_clears_after_timeout(self):
        short_timeout = 2  # Will this make for flakey tests?
        with self.settings(USER_CACHE_TIMEOUT=short_timeout):
            credentials = base64.b64encode(f'{self.user.username}:not_so_top_secret'.encode('utf-8')).decode("utf-8")
            self.client.defaults['HTTP_AUTHORIZATION'] = 'Basic ' + credentials
            resp = self.client.get('/authget')
            self.assertEqual(resp.status_code, 401)

            time.sleep(short_timeout)  # clear the poisoned cache

            credentials = base64.b64encode(f'{self.user.username}:top_secret'.encode('utf-8')).decode("utf-8")
            self.client.defaults['HTTP_AUTHORIZATION'] = 'Basic ' + credentials
            resp = self.client.get('/authget')
            self.assertEqual(resp.status_code, 200)

    def test_invalid_request_fails_after_valid(self):
        decent_timeout = 10  # Will this make for flakey tests?
        with self.settings(USER_CACHE_TIMEOUT=decent_timeout):
            credentials = base64.b64encode(f'{self.user.username}:top_secret'.encode('utf-8')).decode("utf-8")
            self.client.defaults['HTTP_AUTHORIZATION'] = 'Basic ' + credentials
            resp = self.client.get('/authget')
            self.assertEqual(resp.status_code, 200)

            credentials = base64.b64encode(f'{self.user.username}:not_so_top_secret'.encode('utf-8')).decode("utf-8")
            self.client.defaults['HTTP_AUTHORIZATION'] = 'Basic ' + credentials
            resp = self.client.get('/authget')
            self.assertEqual(resp.status_code, 401)

class UtilsTests(TestCase):
    ##
    ## Plumbing methods
    ##

    def setUp(self):
        self.factory = RequestFactory()

    ##
    ## Tests for helper methods
    ##

    # def get_credentials(request):
    def test_get_credentials(self):
        # TODO: probably more tests
        inusername = 'da_username'
        inpassword = 'da_password'

        auth_headers = {
            'HTTP_AUTHORIZATION':
            'Basic ' + base64.b64encode(f'{inusername}:{inpassword}'.encode("utf-8")).decode("utf-8"),
        }
        request = self.factory.get('/hello', **auth_headers)
        username, password = get_credentials(request)

        self.assertEqual(inusername, username)
        self.assertEqual(inpassword, password)

