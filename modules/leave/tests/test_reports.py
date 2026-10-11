"""Tests for administrative leave reports."""

from datetime import date
from types import SimpleNamespace

import pytest

from core.api.exceptions import BadRequestError, PermissionDeniedError
from modules.leave.models import LeaveApplication
from modules.leave.services.reports import list_leave_report

pytestmark = pytest.mark.django_db

REPORT_PERMISSION = {"leave.report.view"}


def make_actor(user_id=900, permissions=None):
    if permissions is None:
        permissions = REPORT_PERMISSION

    return SimpleNamespace(
        user_id=user_id,
        is_authenticated=True,
        has_permission=lambda code: code in permissions,
    )


def create_leave(
    user_id,
    category="EL",
    status="pending",
    start_date=date(2026, 11, 2),
    end_date=date(2026, 11, 3),
):
    return LeaveApplication.objects.create(
        user_id=user_id,
        category=category,
        start_date=start_date,
        end_date=end_date,
        reason="Report test",
        status=status,
    )


def test_report_requires_permission():
    create_leave(101)

    with pytest.raises(PermissionDeniedError):
        list_leave_report(actor=make_actor(permissions=set()))

    assert LeaveApplication.objects.count() == 1


def test_report_returns_records_for_all_employees():
    first = create_leave(101)
    second = create_leave(202)

    results = list(list_leave_report(actor=make_actor()))

    assert {item.pk for item in results} == {first.pk, second.pk}


def test_report_filters_by_employee_category_and_status():
    matching = create_leave(101, category="CL", status="approved")
    create_leave(202, category="EL", status="pending")
    create_leave(101, category="CL", status="rejected")

    results = list(
        list_leave_report(
            actor=make_actor(),
            employee_user_id=101,
            category="CL",
            status="approved",
        )
    )

    assert [item.pk for item in results] == [matching.pk]


def test_report_filters_by_overlapping_date_range():
    matching = create_leave(
        101,
        start_date=date(2026, 11, 1),
        end_date=date(2026, 11, 5),
    )
    create_leave(
        202,
        start_date=date(2026, 11, 6),
        end_date=date(2026, 11, 8),
    )

    results = list(
        list_leave_report(
            actor=make_actor(),
            start_date=date(2026, 11, 3),
            end_date=date(2026, 11, 4),
        )
    )

    assert [item.pk for item in results] == [matching.pk]


@pytest.mark.parametrize(
    ("filters", "message"),
    [
        ({"category": "INVALID"}, "category"),
        ({"status": "INVALID"}, "status"),
        ({"employee_user_id": 0}, "Employee user ID"),
        (
            {
                "start_date": date(2026, 11, 5),
                "end_date": date(2026, 11, 2),
            },
            "Start date",
        ),
    ],
)
def test_report_rejects_invalid_filters(filters, message):
    with pytest.raises(BadRequestError, match=message):
        list_leave_report(actor=make_actor(), **filters)
