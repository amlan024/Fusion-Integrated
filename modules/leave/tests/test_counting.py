from datetime import date

import pytest

from modules.leave.domain.counting import count_chargeable_days


@pytest.fixture
def mock_holidays():
    return {date(2023, 1, 1), date(2023, 1, 2), date(2023, 1, 3)}

def test_count_chargeable_days_single_day_inclusive(mock_holidays):
    start_date = date(2023, 1, 1)
    end_date = date(2023, 1, 1)
    assert count_chargeable_days('CL', start_date, end_date, mock_holidays) == 0
    assert count_chargeable_days('EL', start_date, end_date, mock_holidays) == 1

def test_count_chargeable_days_multi_day_inclusive(mock_holidays):
    start_date = date(2023, 1, 1)
    end_date = date(2023, 1, 3)
    assert count_chargeable_days('CL', start_date, end_date, mock_holidays) == 0
    assert count_chargeable_days('EL', start_date, end_date, mock_holidays) == 3

def test_count_chargeable_days_monday_to_friday(mock_holidays):
    start_date = date(2023, 1, 4)
    end_date = date(2023, 1, 10)
    assert count_chargeable_days('CL', start_date, end_date, mock_holidays) == 5
    assert count_chargeable_days('EL', start_date, end_date, mock_holidays) == 7

def test_count_chargeable_days_weekends_inclusive(mock_holidays):
    start_date = date(2023, 1, 1)
    end_date = date(2023, 1, 5)
    assert count_chargeable_days('CL', start_date, end_date, mock_holidays) == 2
    assert count_chargeable_days('EL', start_date, end_date, mock_holidays) == 5

def test_count_chargeable_days_holidays_on_weekdays(mock_holidays):
    start_date = date(2023, 1, 1)
    end_date = date(2023, 1, 5)
    assert count_chargeable_days('CL', start_date, end_date, mock_holidays) == 2
    assert count_chargeable_days('EL', start_date, end_date, mock_holidays) == 5

def test_count_chargeable_days_holidays_on_weekends(mock_holidays):
    start_date = date(2023, 1, 2)
    end_date = date(2023, 1, 5)
    assert count_chargeable_days('CL', start_date, end_date, mock_holidays) == 2
    assert count_chargeable_days('EL', start_date, end_date, mock_holidays) == 4

def test_none_holidays(mock_holidays):
    start_date = date(2023, 1, 1)
    end_date = date(2023, 1, 5)
    assert count_chargeable_days('CL', start_date, end_date, None) == 4
    assert count_chargeable_days('EL', start_date, end_date, None) == 5

def test_explicit_holidays(mock_holidays):
    start_date = date(2023, 1, 1)
    end_date = date(2023, 1, 5)
    assert count_chargeable_days('CL', start_date, end_date, mock_holidays) == 2
    assert count_chargeable_days('EL', start_date, end_date, mock_holidays) == 5

def test_categories_for_jan1_to_5(mock_holidays):
    # January 1 alone
    start_date = date(2023, 1, 1)
    end_date = date(2023, 1, 1)
    expected_values = [0, 0, 0, 1, 1, 1]
    for category in ['CL', 'RH', 'SCL', 'EL', 'COL', 'VL']:
        assert count_chargeable_days(category, start_date, end_date, mock_holidays) == expected_values.pop(0)

    # January 1-3
    start_date = date(2023, 1, 1)
    end_date = date(2023, 1, 3)
    expected_values = [0, 0, 0, 3, 3, 3]
    for category in ['CL', 'RH', 'SCL', 'EL', 'COL', 'VL']:
        assert count_chargeable_days(category, start_date, end_date, mock_holidays) == expected_values.pop(0)

    # January 4-10 without holidays
    start_date = date(2023, 1, 4)
    end_date = date(2023, 1, 10)
    expected_values = [5, 5, 5, 7, 7, 7]
    for category in ['CL', 'RH', 'SCL', 'EL', 'COL', 'VL']:
        assert count_chargeable_days(category, start_date, end_date, None) == expected_values.pop(0)

    # January 1-5 without holidays
    start_date = date(2023, 1, 1)
    end_date = date(2023, 1, 5)
    expected_values = [4, 4, 4, 5, 5, 5]
    for category in ['CL', 'RH', 'SCL', 'EL', 'COL', 'VL']:
        assert count_chargeable_days(category, start_date, end_date, None) == expected_values.pop(0)

    # January 1-5 with mock holidays
    start_date = date(2023, 1, 1)
    end_date = date(2023, 1, 5)
    expected_values = [2, 2, 2, 5, 5, 5]
    for category in ['CL', 'RH', 'SCL', 'EL', 'COL', 'VL']:
        assert count_chargeable_days(category, start_date, end_date, mock_holidays) == expected_values.pop(0)

    # January 2-5 with mock holidays
    start_date = date(2023, 1, 2)
    end_date = date(2023, 1, 5)
    expected_values = [2, 2, 2, 4, 4, 4]
    for category in ['CL', 'RH', 'SCL', 'EL', 'COL', 'VL']:
        assert count_chargeable_days(category, start_date, end_date, mock_holidays) == expected_values.pop(0)

def test_invalid_category(mock_holidays):
    with pytest.raises(ValueError):
        count_chargeable_days('INVALID', date(2023, 1, 1), date(2023, 1, 1), mock_holidays)

def test_end_before_start(mock_holidays):
    with pytest.raises(ValueError):
        count_chargeable_days('CL', date(2023, 1, 5), date(2023, 1, 1), mock_holidays)

def test_holiday_set_immutable(mock_holidays):
    original_holidays = set(mock_holidays)
    count_chargeable_days('CL', date(2023, 1, 1), date(2023, 1, 5), mock_holidays)
    assert original_holidays == mock_holidays
