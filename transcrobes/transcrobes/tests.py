# -*- coding: utf-8 -*-
import json
import logging

from django.core.exceptions import SuspiciousOperation
from django.contrib.auth.models import AnonymousUser, User
from django.test import RequestFactory, TestCase

from .views import auth

class AuthTests(TestCase):
    def setUp(self):
        # Every test needs access to the request factory.
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            username='toto', email='toto@transcrob.es', password='top_secret')

    def test_valid_user_succeeds(self):
        data = { 'username': 'toto', 'password': 'top_secret' }
        request = self.factory.post('/auth', data, content_type='application/json')

        request.user = AnonymousUser()

        response = auth(request)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(json.loads(response.content)['valid_user'] == True)

    def test_invalid_user_fails(self):
        data = { 'username': 'toto', 'password': 'not_so_top_secret' }
        request = self.factory.post('/auth', data, content_type='application/json')

        request.user = AnonymousUser()

        response = auth(request)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(json.loads(response.content)['valid_user'] == False)

    def test_invalid_request_fails(self):
        data = { 'username': 'missing_the_password' }
        request = self.factory.post('/auth', data, content_type='application/json')
        request.user = AnonymousUser()
        with self.assertRaises(SuspiciousOperation):
            response = auth(request)
