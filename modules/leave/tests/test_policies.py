
"""Tests for leave policy administration."""

from types import SimpleNamespace

import pytest

from core.api.exceptions import (
    BadRequestError,
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
)
from modules.leave.models import LeavePolicy
from modules.leave.services import policies

pytestmark = pytest.mark.django_db


def make_actor(user_id=900, allowed=True):
    return SimpleNamespace(
        user_id=user_id,
        is_authenticated=True,
        has_permission=lambda permission: (
            allowed and permission == "leave.policy.manage"
        ),
    )


def create_policy(**overrides):
    arguments = {
        "actor": make_actor(),
        "category": "CL",
        "faculty_entitlement": 8,
        "staff_entitlement": 8,
    }
    arguments.update(overrides)
    return policies.create_policy(**arguments)


def test_create_policy_saves_entitlements():
    policy = create_policy(faculty_entitlement="8.00", staff_entitlement="7.50")

    assert policy.category == "CL"
    assert policy.faculty_entitlement == 8
    assert policy.staff_entitlement == 7.5
    assert LeavePolicy.objects.count() == 1


def test_policy_creation_requires_permission():
    with pytest.raises(PermissionDeniedError):
        create_policy(actor=make_actor(allowed=False))

    assert LeavePolicy.objects.count() == 0


def test_policy_creation_requires_integer_user_id():
    actor = make_actor(user_id="900")

    with pytest.raises(PermissionDeniedError):
        create_policy(actor=actor)


def test_invalid_category_is_rejected():
    with pytest.raises(BadRequestError):
        create_policy(category="XYZ")


@pytest.mark.parametrize("value", [-1, "-0.01", "NaN", "Infinity", "1.234"])
def test_invalid_entitlement_is_rejected(value):
    with pytest.raises(BadRequestError):
        create_policy(faculty_entitlement=value)


def test_non_numeric_entitlement_is_rejected():
    with pytest.raises(BadRequestError):
        create_policy(staff_entitlement="eight")


def test_non_boolean_policy_flag_is_rejected():
    with pytest.raises(BadRequestError):
        create_policy(carries_forward=1)


def test_duplicate_category_policy_is_rejected():
    create_policy()

    with pytest.raises(ConflictError):
        create_policy()


def test_update_policy_changes_current_policy():
    policy = create_policy()

    updated = policies.update_policy(
        actor=make_actor(),
        policy_id=policy.pk,
        faculty_entitlement="9.5",
        staff_entitlement="8",
        requires_col_eligibility=False,
        counts_weekends=True,
        counts_public_holidays=True,
        carries_forward=True,
        enabled=True,
    )

    assert updated.pk == policy.pk
    assert updated.faculty_entitlement == 9.5
    assert updated.staff_entitlement == 8
    assert updated.counts_weekends is True
    assert updated.carries_forward is True


def test_update_policy_requires_permission():
    policy = create_policy()

    with pytest.raises(PermissionDeniedError):
        policies.update_policy(
            actor=make_actor(allowed=False),
            policy_id=policy.pk,
            faculty_entitlement=9,
            staff_entitlement=8,
            requires_col_eligibility=False,
            counts_weekends=False,
            counts_public_holidays=False,
            carries_forward=False,
            enabled=True,
        )

    policy.refresh_from_db()
    assert policy.faculty_entitlement == 8


def test_update_unknown_policy_raises_not_found():
    with pytest.raises(NotFoundError):
        policies.update_policy(
            actor=make_actor(),
            policy_id=999999,
            faculty_entitlement=9,
            staff_entitlement=8,
            requires_col_eligibility=False,
            counts_weekends=False,
            counts_public_holidays=False,
            carries_forward=False,
            enabled=True,
        )


def test_list_policies_returns_categories_in_order():
    create_policy(category="RH", faculty_entitlement=2, staff_entitlement=2)
    create_policy(category="CL", faculty_entitlement=8, staff_entitlement=8)

    result = policies.list_policies(actor=make_actor())

    assert list(result.values_list("category", flat=True)) == ["CL", "RH"]


def test_list_policies_requires_permission():
    with pytest.raises(PermissionDeniedError):
        policies.list_policies(actor=make_actor(allowed=False))
