import re
from django.contrib.auth.backends import ModelBackend
from apps.users.models import User

class UsernameMobileModelBackend(ModelBackend):

    def authenticate(self, request, username=None, password=None, **kwargs):

        if re.match(r'1[3-9]\d{9}',username):
            user = User.objects.get(mobile=username)
        else:
            username = User.objects.get(username=username)
        if user and user.check_password(password):
            return user

        return None

