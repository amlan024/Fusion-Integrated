"""Tests for employee leave application services."""

from datetime import date
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from core.api.exceptions import (
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
)
from modules.leave.models import LeaveApplication
from modules.leave.services import applications

pytestmark = pytest.mark.django_db


def make_actor(user_id, permissions):
    """Create a lightweight test actor with explicit permissions."""
    return SimpleNamespace(
        user_id=user_id,
        is_authenticated=True,
        has_permission=lambda permission: permission in permissions,
    )


EMPLOYEE_PERMISSIONS = {
    "leave.application.create",
    "leave.application.view_self",
    "leave.application.withdraw",
}


def create_leave(user_id, status="pending"):
    return LeaveApplication.objects.create(
        user_id=user_id,
        category="EL",
        start_date=date(2026, 11, 2),
        end_date=date(2026, 11, 3),
        reason="Personal work",
        status=status,
    )


def test_employee_without_permission_cannot_submit():
    actor = make_actor(101, set())

    with pytest.raises(PermissionDeniedError):
        applications.create_application(
            actor=actor,
            category="CL",
            start_date=date(2026, 11, 2),
            end_date=date(2026, 11, 2),
            reason="Personal work",
        )

    assert LeaveApplication.objects.count() == 0


def test_authorized_employee_can_submit_application():
    actor = make_actor(101, EMPLOYEE_PERMISSIONS)

    application = applications.create_application(
        actor=actor,
        category="CL",
        start_date=date(2026, 11, 2),
        end_date=date(2026, 11, 2),
        reason="Personal work",
    )

    assert application.user_id == 101
    assert application.category == "CL"
    assert application.status == "pending"


@pytest.mark.parametrize("status", ["pending", "approved"])
def test_overlapping_active_leave_is_rejected(status):
    actor = make_actor(101, EMPLOYEE_PERMISSIONS)
    create_leave(101, status=status)

    with pytest.raises(ConflictError):
        applications.create_application(
            actor=actor,
            category="EL",
            start_date=date(2026, 11, 3),
            end_date=date(2026, 11, 4),
            reason="Another request",
        )


def test_employee_cannot_view_another_employees_applications():
    actor = make_actor(101, EMPLOYEE_PERMISSIONS)
    create_leave(202)

    results = applications.list_own_applications(actor=actor)

    assert list(results.values_list("user_id", flat=True)) == []


def test_employee_cannot_withdraw_another_employees_application():
    actor = make_actor(101, EMPLOYEE_PERMISSIONS)
    foreign_application = create_leave(202)

    with pytest.raises(NotFoundError):
        applications.withdraw_application(
            actor=actor,
            application_id=foreign_application.pk,
        )

    foreign_application.refresh_from_db()
    assert foreign_application.status == "pending"


def test_employee_can_withdraw_own_pending_application():
    actor = make_actor(101, EMPLOYEE_PERMISSIONS)
    application = create_leave(101)

    result = applications.withdraw_application(
        actor=actor,
        application_id=application.pk,
    )

    assert result.status == "withdrawn"


def test_employee_cannot_withdraw_non_pending_application():
    actor = make_actor(101, EMPLOYEE_PERMISSIONS)
    application = create_leave(101, status="approved")

    with pytest.raises(ConflictError):
        applications.withdraw_application(
            actor=actor,
            application_id=application.pk,
        )

    application.refresh_from_db()
    assert application.status == "approved"


def test_opposite_half_day_cl_requests_can_coexist():
    actor = make_actor(101, EMPLOYEE_PERMISSIONS)

    with patch.object(
        applications,
        "check_leave_overlap",
        wraps=applications.check_leave_overlap,
    ):
        first = applications.create_application(
            actor=actor,
            category="CL",
            start_date=date(2026, 11, 2),
            end_date=date(2026, 11, 2),
            reason="First half",
            half_day="first_half",
        )
        second = applications.create_application(
            actor=actor,
            category="CL",
            start_date=date(2026, 11, 2),
            end_date=date(2026, 11, 2),
            reason="Second half",
            half_day="second_half",
        )

    assert first.status == "pending"
    assert second.status == "pending"
