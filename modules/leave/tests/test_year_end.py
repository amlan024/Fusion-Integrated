"""Tests for database-backed year-end processing."""

from decimal import Decimal
from types import SimpleNamespace

import pytest

from core.api.exceptions import BadRequestError, ConflictError, PermissionDeniedError
from modules.leave.models import LeaveAccount
from modules.leave.services.year_end import process_year_end

pytestmark = pytest.mark.django_db

YEAR_END_PERMISSION = {"leave.year_end.process"}


def make_actor(permissions=None):
    if permissions is None:
        permissions = YEAR_END_PERMISSION

    return SimpleNamespace(
        user_id=900,
        is_authenticated=True,
        has_permission=lambda code: code in permissions,
    )


def create_account(user_id, category, balance, year=2026):
    return LeaveAccount.objects.create(
        user_id=user_id,
        category=category,
        year=year,
        opening_balance=Decimal(str(balance)),
    )


def test_year_end_lapses_expiring_leave_and_carries_forward():
    create_account(101, "CL", 5)
    create_account(101, "EL", 10)
    create_account(101, "COL", 4)

    result = process_year_end(actor=make_actor(), year=2026)

    assert result == {
        "year": 2026,
        "next_year": 2027,
        "employees_processed": 1,
    }

    next_accounts = {
        account.category: account
        for account in LeaveAccount.objects.filter(user_id=101, year=2027)
    }

    assert next_accounts["CL"].balance == 0
    assert next_accounts["EL"].balance == 10
    assert next_accounts["COL"].balance == 4


def test_faculty_vacation_converts_to_earned_leave():
    create_account(101, "VL", 5)
    create_account(101, "EL", 10)

    process_year_end(
        actor=make_actor(),
        year=2026,
        faculty_user_ids={101},
    )

    next_accounts = {
        account.category: account
        for account in LeaveAccount.objects.filter(user_id=101, year=2027)
    }

    assert next_accounts["VL"].balance == 0
    assert next_accounts["EL"].balance == Decimal("12.5")


def test_year_end_requires_permission():
    create_account(101, "CL", 5)

    with pytest.raises(PermissionDeniedError):
        process_year_end(actor=make_actor(set()), year=2026)

def test_year_end_rejects_invalid_year():
    with pytest.raises(BadRequestError):
        process_year_end(actor=make_actor(), year=-1)


def test_existing_next_year_accounts_prevent_duplicate_processing():
    create_account(101, "CL", 5)
    create_account(202, "EL", 10, year=2027)

    with pytest.raises(ConflictError):
        process_year_end(actor=make_actor(), year=2026)
