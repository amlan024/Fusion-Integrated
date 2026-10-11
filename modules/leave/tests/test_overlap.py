
from copy import deepcopy
from datetime import date, datetime

import pytest

from modules.leave.domain.overlap import check_leave_overlap


def request(start, end, category="CL", half_day=None, include_half=True):
    item = {
        "start_date": date.fromisoformat(start),
        "end_date": date.fromisoformat(end),
        "category": category,
    }
    if include_half:
        item["half_day"] = half_day
    return item


def existing(start, end, category="CL", status="pending",
             half_day=None, include_half=True):
    item = request(start, end, category, half_day, include_half)
    item["status"] = status
    return item


def test_same_category_overlap():
    new = request("2023-01-01", "2023-01-05")
    old = existing("2023-01-04", "2023-01-08")
    assert check_leave_overlap(new, [old]) == [old]


def test_cl_and_rh_overlap():
    new = request("2023-01-01", "2023-01-05", "CL")
    old = existing("2023-01-04", "2023-01-08", "RH")
    assert check_leave_overlap(new, [old]) == [old]


def test_disjoint_dates():
    new = request("2023-01-01", "2023-01-03")
    old = existing("2023-01-10", "2023-01-12")
    assert check_leave_overlap(new, [old]) == []


def test_adjacent_dates_without_shared_date():
    new = request("2023-01-01", "2023-01-03")
    old = existing("2023-01-04", "2023-01-06")
    assert check_leave_overlap(new, [old]) == []


@pytest.mark.parametrize("status", ["pending", "approved"])
def test_pending_and_approved_overlaps_conflict(status):
    new = request("2023-01-05", "2023-01-07")
    old = existing("2023-01-06", "2023-01-08", status=status)
    assert check_leave_overlap(new, [old]) == [old]


@pytest.mark.parametrize("status", ["rejected", "withdrawn", "cancelled"])
def test_terminal_status_does_not_block(status):
    new = request("2023-01-05", "2023-01-07")
    old = existing("2023-01-06", "2023-01-08", status=status)
    assert check_leave_overlap(new, [old]) == []


@pytest.mark.parametrize(
    ("new_half", "old_half"),
    [("first_half", "second_half"), ("second_half", "first_half")],
)
def test_opposite_half_days_do_not_conflict(new_half, old_half):
    new = request("2023-01-05", "2023-01-05", half_day=new_half)
    old = existing("2023-01-05", "2023-01-05", half_day=old_half)
    assert check_leave_overlap(new, [old]) == []


def test_same_half_days_conflict():
    new = request("2023-01-05", "2023-01-05", half_day="first_half")
    old = existing("2023-01-05", "2023-01-05", half_day="first_half")
    assert check_leave_overlap(new, [old]) == [old]


@pytest.mark.parametrize("new_is_half_day", [True, False])
def test_full_day_and_half_day_conflict_both_directions(new_is_half_day):
    half = "first_half" if new_is_half_day else None
    new = request("2023-01-05", "2023-01-05", half_day=half)
    old_half = None if new_is_half_day else "first_half"
    old = existing("2023-01-05", "2023-01-05", half_day=old_half)
    assert check_leave_overlap(new, [old]) == [old]


def test_half_day_cl_overlaps_another_category():
    new = request("2023-01-05", "2023-01-05", "CL", "first_half")
    old = existing("2023-01-05", "2023-01-05", "RH")
    assert check_leave_overlap(new, [old]) == [old]


@pytest.mark.parametrize("include_half,value", [(False, None), (True, None)])
def test_missing_or_none_half_day_means_full_day(include_half, value):
    new = request(
        "2023-01-05", "2023-01-05",
        half_day=value, include_half=include_half,
    )
    old = existing(
        "2023-01-05", "2023-01-05", half_day="first_half"
    )
    assert check_leave_overlap(new, [old]) == [old]


def test_multiday_half_day_is_invalid():
    new = request("2023-01-05", "2023-01-06", half_day="first_half")
    with pytest.raises(ValueError):
        check_leave_overlap(new, [])


def test_invalid_category():
    new = request("2023-01-05", "2023-01-05", category="INVALID")
    with pytest.raises(ValueError):
        check_leave_overlap(new, [])


def test_invalid_existing_status():
    new = request("2023-01-05", "2023-01-05")
    old = existing("2023-01-05", "2023-01-05", status="invalid")
    with pytest.raises(ValueError):
        check_leave_overlap(new, [old])


def test_invalid_date_order():
    new = request("2023-01-06", "2023-01-05")
    with pytest.raises(ValueError):
        check_leave_overlap(new, [])


@pytest.mark.parametrize(
    "bad_date",
    ["2023-01-05", datetime(2023, 1, 5)],
)
def test_invalid_date_types(bad_date):
    new = {
        "start_date": bad_date,
        "end_date": date(2023, 1, 6),
        "category": "CL",
    }
    with pytest.raises(TypeError):
        check_leave_overlap(new, [])


def test_datetime_end_date_is_invalid():
    new = {
        "start_date": date(2023, 1, 5),
        "end_date": datetime(2023, 1, 6),
        "category": "CL",
    }
    with pytest.raises(TypeError):
        check_leave_overlap(new, [])


def test_invalid_half_day_value():
    new = request("2023-01-05", "2023-01-05", half_day="morning")
    with pytest.raises(ValueError):
        check_leave_overlap(new, [])


def test_half_day_on_non_cl_category_is_invalid():
    new = request(
        "2023-01-05", "2023-01-05", "RH", "first_half"
    )
    with pytest.raises(ValueError):
        check_leave_overlap(new, [])


def test_malformed_terminal_request_is_still_validated():
    new = request("2023-01-05", "2023-01-05")
    old = existing(
        "2023-01-05", "2023-01-05", status="rejected"
    )
    old["category"] = "INVALID"
    with pytest.raises(ValueError):
        check_leave_overlap(new, [old])

def test_non_dictionary_request_raises_type_error():
    with pytest.raises(TypeError):
        check_leave_overlap("not a request", [])


def test_new_request_does_not_require_status():
    new = request("2023-01-05", "2023-01-05")
    old = existing("2023-01-05", "2023-01-05")
    assert check_leave_overlap(new, [old]) == [old]


def test_inputs_unchanged_and_conflicts_keep_identity_and_order():
    new = request("2023-01-05", "2023-01-08")
    first = existing("2023-01-06", "2023-01-07")
    terminal = existing(
        "2023-01-05", "2023-01-06", status="withdrawn"
    )
    second = existing("2023-01-08", "2023-01-09")
    items = [first, terminal, second]

    new_before = deepcopy(new)
    items_before = deepcopy(items)

    result = check_leave_overlap(new, items)

    assert len(result) == 2
    assert result[0] is first
    assert result[1] is second
    assert new == new_before
    assert items == items_before
