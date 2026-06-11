from __future__ import annotations

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.db.models import Q


class UsernameOrEmailBackend(ModelBackend):
    """Authenticate staff with either their username or a unique email address."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        login = username or kwargs.get("email")
        if login is None or password is None:
            return None

        user_model = get_user_model()
        users = user_model._default_manager.filter(Q(username__iexact=login) | Q(email__iexact=login))
        if users.count() != 1:
            return None

        user = users.get()
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
