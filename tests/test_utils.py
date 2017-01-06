# -*- coding: utf-8 -*-
from django.contrib.auth import get_user_model
from django.http import HttpRequest
from django.test import TestCase

from collections import OrderedDict


from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

UserModel = get_user_model()


class BaseTestCase(TestCase):
    maxDiff = None
    password = "dump-password"

    def toDict(self, obj):
        """
            Helper function to make errors in tests more readable - use to parse answer before compare
        """
        if not isinstance(obj, (dict, list, OrderedDict)):
            return obj
        if isinstance(obj, OrderedDict):
            obj = dict(obj)
        for k, v in obj.items():
            new_v = v
            if isinstance(v, list):
                new_v = []
                for v2 in v:
                    v2 = self.toDict(v2)
                    new_v.append(v2)
            elif isinstance(v, OrderedDict):
                new_v = dict(v)
            obj[k] = new_v
        return obj

    def get_context(self, user=None):
        if user is None:
            user = self.user
        request = HttpRequest()
        request.user = user
        context = {
            'request': request
        }
        return context

    def _login(self):
        self.client.login(email='joe+1@doe.com', password=self.password)

    def _new_user(self, i, is_active=True):
        user = UserModel.objects.create(
            first_name='Joe%i' % i,
            last_name='Doe',
            email='joe+%s@doe.com' % i,
            is_active=is_active,
            # zipcode='11111',
            )
        user.set_password(self.password)
        user.save()
        return user

    def _create_user(self, i=1):
        self.user = self._new_user(i)
        return self.user


class APIBaseTestCase(BaseTestCase, APITestCase):

    def _login(self):
        email = 'joe+1@doe.com'
        user = UserModel.objects.get(email=email)
        token = Token.objects.create(user=user)
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + token.key)
        return self.client.login(email=email, password=self.password)
