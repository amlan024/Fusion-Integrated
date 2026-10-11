"""Tests for employee leave balance queries."""

from types import SimpleNamespace

import pytest

from core.api.exceptions import PermissionDeniedError
from modules.leave.models import LeaveAccount
from modules.leave.services.balances import list_own_balances

pytestmark = pytest.mark.django_db


def make_actor(user_id, allowed=True):
    return SimpleNamespace(
        user_id=user_id,
        is_authenticated=True,
        has_permission=lambda permission: (
            allowed and permission == "leave.balance.view_self"
        ),
    )


def test_employee_sees_only_own_balances():
    LeaveAccount.objects.create(
        user_id=101,
        category="CL",
        year=2026,
        opening_balance=8,
    )
    LeaveAccount.objects.create(
        user_id=202,
        category="CL",
        year=2026,
        opening_balance=8,
    )

    results = list(list_own_balances(actor=make_actor(101)))

    assert len(results) == 1
    assert results[0].user_id == 101
    assert results[0].balance == 8


def test_employee_without_permission_cannot_view_balances():
    with pytest.raises(PermissionDeniedError):
        list_own_balances(actor=make_actor(101, allowed=False))
