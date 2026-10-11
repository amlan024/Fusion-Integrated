"""Tests for leave calendar management."""

from datetime import date
from types import SimpleNamespace

import pytest

from core.api.exceptions import (
    BadRequestError,
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
)
from modules.leave.models import LeaveCalendarEntry
from modules.leave.services import calendar

pytestmark = pytest.mark.django_db


def make_actor(user_id=900, allowed=True):
    return SimpleNamespace(
        user_id=user_id,
        is_authenticated=True,
        has_permission=lambda permission: (
            allowed and permission == "leave.calendar.manage"
        ),
    )


def test_calendar_entry_starts_unpublished():
    entry = calendar.create_calendar_entry(
        actor=make_actor(),
        entry_type="holiday",
        entry_date=date(2026, 12, 25),
        name="Winter Holiday",
    )

    assert entry.is_published is False


def test_calendar_management_requires_permission():
    with pytest.raises(PermissionDeniedError):
        calendar.create_calendar_entry(
            actor=make_actor(allowed=False),
            entry_type="holiday",
            entry_date=date(2026, 12, 25),
            name="Winter Holiday",
        )

    assert LeaveCalendarEntry.objects.count() == 0


def test_invalid_calendar_type_is_rejected():
    with pytest.raises(BadRequestError):
        calendar.create_calendar_entry(
            actor=make_actor(),
            entry_type="unknown",
            entry_date=date(2026, 12, 25),
            name="Winter Holiday",
        )


def test_duplicate_calendar_entry_is_rejected():
    arguments = {
        "actor": make_actor(),
        "entry_type": "rh",
        "entry_date": date(2026, 11, 10),
        "name": "Restricted Holiday",
    }

    calendar.create_calendar_entry(**arguments)

    with pytest.raises(ConflictError):
        calendar.create_calendar_entry(**arguments)


def test_publishing_makes_entry_available_for_queries():
    entry = calendar.create_calendar_entry(
        actor=make_actor(),
        entry_type="rh",
        entry_date=date(2026, 11, 10),
        name="Restricted Holiday",
    )

    assert list(
        calendar.list_published_calendar_entries(
            start_date=date(2026, 11, 1),
            end_date=date(2026, 11, 30),
            entry_type="rh",
        )
    ) == []

    calendar.publish_calendar_entry(
        actor=make_actor(),
        entry_id=entry.pk,
    )

    results = calendar.list_published_calendar_entries(
        start_date=date(2026, 11, 1),
        end_date=date(2026, 11, 30),
        entry_type="rh",
    )

    assert list(results.values_list("pk", flat=True)) == [entry.pk]


def test_publishing_unknown_entry_raises_not_found():
    with pytest.raises(NotFoundError):
        calendar.publish_calendar_entry(
            actor=make_actor(),
            entry_id=999999,
        )


def test_invalid_date_range_is_rejected():
    with pytest.raises(BadRequestError):
        calendar.list_published_calendar_entries(
            start_date=date(2026, 12, 31),
            end_date=date(2026, 12, 1),
        )
