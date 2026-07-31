from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.hashers import check_password
from .models import User


class OfficeSharedPasswordBackend(BaseBackend):
    """Users authenticate with their own unique email + their office's shared password."""

    def authenticate(self, request, email=None, password=None, **kwargs):
        if not email or not password:
            return None
        try:
            user = User.objects.select_related("office").get(email=email, is_active=True)
        except User.DoesNotExist:
            return None

        if user.office and user.office.shared_password_hash and check_password(password, user.office.shared_password_hash):
            return user
        return None

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None