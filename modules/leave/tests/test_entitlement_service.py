
"""Tests for database-backed entitlement calculations."""

from decimal import Decimal

import pytest

from modules.leave.models import LeavePolicy
from modules.leave.services.entitlements import get_annual_entitlement

pytestmark = pytest.mark.django_db


def test_uses_default_entitlement_when_policy_is_missing():
    assert get_annual_entitlement(category="CL", is_faculty=True) == 8
    assert get_annual_entitlement(category="EL", is_faculty=False) == 30


def test_uses_custom_entitlement_from_current_policy():
    LeavePolicy.objects.create(
        category="CL",
        faculty_entitlement=Decimal("10.00"),
        staff_entitlement=Decimal("6.00"),
    )

    assert get_annual_entitlement(category="CL", is_faculty=True) == 10
    assert get_annual_entitlement(category="CL", is_faculty=False) == 6


def test_disabled_policy_returns_zero():
    LeavePolicy.objects.create(
        category="CL",
        faculty_entitlement=Decimal("10.00"),
        staff_entitlement=Decimal("6.00"),
        enabled=False,
    )

    assert get_annual_entitlement(category="CL", is_faculty=True) == 0


def test_col_policy_checks_eligibility():
    LeavePolicy.objects.create(
        category="COL",
        faculty_entitlement=Decimal("20.00"),
        staff_entitlement=Decimal("20.00"),
        requires_col_eligibility=True,
    )

    assert (
        get_annual_entitlement(
            category="COL",
            is_faculty=False,
            col_eligible=False,
        )
        == 0
    )
    assert (
        get_annual_entitlement(
            category="COL",
            is_faculty=False,
            col_eligible=True,
        )
        == 20
    )
