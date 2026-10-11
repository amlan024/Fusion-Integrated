"""Calendar management and published-calendar queries for ELM."""

from datetime import date

from django.db import IntegrityError, transaction

from core.api.exceptions import BadRequestError, ConflictError
from modules.leave.models import LeaveCalendarEntry
from modules.leave.services.authz import require_permission, require_user_id

VALID_ENTRY_TYPES = {"holiday", "rh", "vacation"}


def _validate_entry(
    *,
    entry_type: str,
    entry_date: date,
    name: str,
    description: str,
) -> tuple[str, date, str, str]:
    if entry_type not in VALID_ENTRY_TYPES:
        raise BadRequestError("Invalid calendar entry type.")

    if not isinstance(entry_date, date):
        raise BadRequestError("Calendar date must be a date.")

    if not isinstance(name, str) or not name.strip():
        raise BadRequestError("Calendar entry name is required.")

    if not isinstance(description, str):
        raise BadRequestError("Description must be text.")

    return entry_type, entry_date, name.strip(), description.strip()


@transaction.atomic
def create_calendar_entry(
    *,
    actor,
    entry_type: str,
    entry_date: date,
    name: str,
    description: str = "",
) -> LeaveCalendarEntry:
    """Create an unpublished calendar entry for an authorized administrator."""
    require_permission(actor, "leave.calendar.manage")
    require_user_id(actor)

    entry_type, entry_date, name, description = _validate_entry(
        entry_type=entry_type,
        entry_date=entry_date,
        name=name,
        description=description,
    )

    if LeaveCalendarEntry.objects.filter(
        entry_type=entry_type,
        date=entry_date,
        name=name,
    ).exists():
        raise ConflictError("This calendar entry already exists.")

    try:
        return LeaveCalendarEntry.objects.create(
            entry_type=entry_type,
            date=entry_date,
            name=name,
            description=description,
            is_published=False,
        )
    except IntegrityError as exc:
        raise ConflictError("This calendar entry already exists.") from exc


@transaction.atomic
def publish_calendar_entry(
    *,
    actor,
    entry_id: int,
) -> LeaveCalendarEntry:
    """Publish an entry so it can be used by calendar validation."""
    require_permission(actor, "leave.calendar.manage")
    require_user_id(actor)

    entry = LeaveCalendarEntry.objects.select_for_update().filter(
        pk=entry_id
    ).first()

    if entry is None:
        from core.api.exceptions import NotFoundError

        raise NotFoundError("Calendar entry not found.")

    if entry.is_published:
        raise ConflictError("Calendar entry is already published.")

    entry.is_published = True
    entry.save(update_fields=["is_published", "updated_at"])
    return entry


def list_published_calendar_entries(
    *,
    start_date: date,
    end_date: date,
    entry_type: str | None = None,
):
    """Return published entries in a date range for leave validation."""
    if not isinstance(start_date, date) or not isinstance(end_date, date):
        raise BadRequestError("Calendar range must contain valid dates.")

    if start_date > end_date:
        raise BadRequestError("Start date cannot be after end date.")

    entries = LeaveCalendarEntry.objects.filter(
        is_published=True,
        date__range=(start_date, end_date),
    )

    if entry_type is not None:
        if entry_type not in VALID_ENTRY_TYPES:
            raise BadRequestError("Invalid calendar entry type.")
        entries = entries.filter(entry_type=entry_type)

    return entries.order_by("date", "name")
