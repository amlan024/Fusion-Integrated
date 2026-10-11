
from datetime import date


def count_chargeable_days(
    category: str,
    start_date: date,
    end_date: date,
    holidays: set[date] | None = None,
) -> int:
    """Count chargeable leave days according to the category's counting rules."""
    all_day_categories = {"EL", "COL", "VL"}
    weekday_categories = {"CL", "RH", "SCL"}

    if category not in all_day_categories | weekday_categories:
        raise ValueError(f"Unsupported category: {category}")

    if end_date < start_date:
        raise ValueError("End date cannot be earlier than start date.")

    if holidays is None:
        holidays = set()

    count = 0
    current_date = start_date

    while current_date <= end_date:
        if (
            category in all_day_categories
            or (
                category in weekday_categories
                and current_date.weekday() < 5
                and current_date not in holidays
            )
        ):
            count += 1

        current_date += date.resolution

    return count
