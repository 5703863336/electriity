import re
from django.contrib.auth.backends import ModelBackend
from itsdangerous import BadData
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer

from apps.users.models import User
from meiduo_mall import settings


class UsernameMobileModelBackend(ModelBackend):

    def authenticate(self, request, username=None, password=None, **kwargs):

        if re.match(r'1[3-9]\d{9}',username):
            user = User.objects.get(mobile=username)
        else:
            username = User.objects.get(username=username)
        if user and user.check_password(password):
            return user

        return None


def generic_active_email_url(id,email):

    s = Serializer(secret_key=settings.SECRET_KEY,expires_in=3600)

    data = {
        'id':id,
        'email':email,
    }

    serect_data = s.dumps(data)
    return 'http://www.meiduo.site:8000/emailsactive/?token=%s'%serect_data.decode()

def check_active_token(token):

    s = Serializer(secret_key=settings.SECRET_KEY,expires_in=3600)
    try:
        data = s.loads(token)
    except BadData:
        return None
    else:
        return data

def generic_access_token_url(username,mobile):

    s = Serializer(secret_key=settings.SECRET_KEY,expires_in=3600)

    data = {
        'username':username,
        'mobile':mobile,
    }

    serect_data = s.dumps(data)
    return serect_data.decode()

def check_access_token_token(token):

    s = Serializer(secret_key=settings.SECRET_KEY,expires_in=3600)
    try:
        data = s.loads(token)
    except BadData:
        return None
    else:
        return data



