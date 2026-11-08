from datetime import date
from decimal import Decimal

import pytest

from modules.elm.domain.leave_calculations import (
    LeaveCalculationError,
    count_leave_days,
    faculty_vl_to_el,
    half_day_cl_amount,
    half_day_cl_requests_overlap,
    periods_overlap,
    remaining_balance,
    validate_half_day_cl_date,
)


def test_count_calendar_days():
    assert count_leave_days(
        "EL",
        date(2026, 1, 1),
        date(2026, 1, 5),
        count_calendar_days=True,
    ) == Decimal("5")


def test_count_working_days_excluding_weekends_and_holidays():
    assert count_leave_days(
        "CL",
        date(2026, 1, 5),
        date(2026, 1, 9),
        count_calendar_days=False,
        holidays=[date(2026, 1, 7)],
    ) == Decimal("4")


def test_continuous_leave_rejects_working_day_count():
    with pytest.raises(LeaveCalculationError):
        count_leave_days(
            "EL",
            date(2026, 1, 1),
            date(2026, 1, 5),
            count_calendar_days=False,
        )


def test_half_day_cl_amount():
    assert half_day_cl_amount("first") == Decimal("0.5")
    assert half_day_cl_amount("second") == Decimal("0.5")


def test_half_day_cl_rejects_invalid_half():
    with pytest.raises(LeaveCalculationError):
        half_day_cl_amount("third")


def test_half_day_cl_requires_one_date():
    with pytest.raises(LeaveCalculationError):
        validate_half_day_cl_date(
            date(2026, 1, 1),
            date(2026, 1, 2),
            "first",
        )


def test_different_half_day_cl_requests_do_not_overlap():
    assert not half_day_cl_requests_overlap(
        date(2026, 1, 1), "first",
        date(2026, 1, 1), "second",
    )


def test_same_half_day_cl_requests_overlap():
    assert half_day_cl_requests_overlap(
        date(2026, 1, 1), "first",
        date(2026, 1, 1), "first",
    )


def test_periods_overlap():
    assert periods_overlap(
        date(2026, 1, 1), date(2026, 1, 5),
        date(2026, 1, 5), date(2026, 1, 8),
    )


def test_periods_do_not_overlap():
    assert not periods_overlap(
        date(2026, 1, 1), date(2026, 1, 5),
        date(2026, 1, 6), date(2026, 1, 8),
    )


def test_faculty_vl_to_el_conversion():
    assert faculty_vl_to_el(Decimal("15")) == Decimal("7.5")


def test_remaining_balance():
    assert remaining_balance(10, 5, 3) == Decimal("12")


def test_insufficient_balance_is_rejected():
    with pytest.raises(LeaveCalculationError):
        remaining_balance(2, 0, 3)
