"""Year-end processing for employee leave balances."""

from decimal import Decimal

from django.db import transaction

from core.api.exceptions import BadRequestError, ConflictError
from modules.leave.domain.entitlements import calculate_year_end_balances
from modules.leave.models import LeaveAccount
from modules.leave.services.authz import require_permission, require_user_id


@transaction.atomic
def process_year_end(*, actor, year, faculty_user_ids=()):
    """Carry forward balances and lapse or convert expiring leave."""
    require_permission(actor, "leave.year_end.process")
    require_user_id(actor)

    if not isinstance(year, int) or isinstance(year, bool) or year < 2000:
        raise BadRequestError("A valid processing year is required.")

    next_year = year + 1
    faculty_user_ids = set(faculty_user_ids)

    accounts = list(
        LeaveAccount.objects.select_for_update()
        .filter(year=year)
        .order_by("user_id", "category")
    )

    if not accounts:
        raise BadRequestError("No leave accounts exist for the processing year.")

    if LeaveAccount.objects.filter(year=next_year).exists():
        raise ConflictError(
            "Next-year leave accounts already exist; review before processing."
        )

    grouped = {}
    for account in accounts:
        grouped.setdefault(account.user_id, {})[account.category] = account

    processed = 0

    for user_id, category_accounts in grouped.items():
        balances = {
            category: float(account.balance)
            for category, account in category_accounts.items()
        }

        updated = calculate_year_end_balances(
            balances,
            is_faculty=user_id in faculty_user_ids,
        )

        for category, balance in updated.items():
            account = category_accounts.get(category)
            if account is not None:
                account.opening_balance = Decimal(str(balance))
                account.credited = Decimal("0")
                account.used = Decimal("0")
                account.adjusted = Decimal("0")
                account.save(
                    update_fields=[
                        "opening_balance",
                        "credited",
                        "used",
                        "adjusted",
                        "updated_at",
                    ]
                )

        for category, balance in updated.items():
            LeaveAccount.objects.create(
                user_id=user_id,
                category=category,
                year=next_year,
                opening_balance=Decimal(str(balance)),
                credited=Decimal("0"),
                used=Decimal("0"),
                adjusted=Decimal("0"),
            )

        processed += 1

    return {"year": year, "next_year": next_year, "employees_processed": processed}
