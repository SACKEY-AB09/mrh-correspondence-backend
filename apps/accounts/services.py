import re
import secrets
from django.contrib.auth.hashers import make_password
from django.utils import timezone
from django.db import transaction
from .models import User, Office


def generate_user_email(first_name, last_name, office):
    """firstname.lastname@officecode.mrh.gov.gh — adds a number if that's taken."""
    base = re.sub(r"[^a-z.]", "", f"{first_name}.{last_name}".lower())
    domain = f"{office.code.lower()}.mrh.gov.gh"

    email = f"{base}@{domain}"
    suffix = 1
    while User.objects.filter(email=email).exists():
        suffix += 1
        email = f"{base}{suffix}@{domain}"
    return email


def generate_office_password(length=8):
    """A readable random password — letters and digits, no visually-confusable characters."""
    alphabet = "ABCDEFGHJKMNPQRSTUVWXYZabcdefghjkmnpqrstuvwxyz23456789"
    return "".join(secrets.choice(alphabet) for _ in range(length))


@transaction.atomic
def create_user(*, first_name, last_name, role, office, created_by):
    email = generate_user_email(first_name, last_name, office)
    user = User(
        username=email.split("@")[0],
        email=email,
        first_name=first_name,
        last_name=last_name,
        role=role,
        office=office,
    )
    user.set_unusable_password()  # this user logs in via the office's shared password, not this field
    user.save()
    return user


@transaction.atomic
def set_office_password(*, office, raw_password, changed_by):
    from apps.audit.models import AuditLog

    office.shared_password_hash = make_password(raw_password)
    office.password_last_rotated = timezone.now()
    office.save(update_fields=["shared_password_hash", "password_last_rotated"])

    AuditLog.objects.create(
        action_type=AuditLog.ActionType.SECURITY,
        title="Office password rotated",
        description=f"Shared password reset for {office.name} by {changed_by.email}",
        actor=changed_by,
        office=office,
    )
    return raw_password


@transaction.atomic
def create_office(*, name, code, created_by):
    office = Office.objects.create(name=name, code=code)
    raw_password = generate_office_password()
    set_office_password(office=office, raw_password=raw_password, changed_by=created_by)
    return office, raw_password