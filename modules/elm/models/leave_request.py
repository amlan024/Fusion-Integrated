
"""Leave applications and their supporting information."""

from django.db import models
from django.db.models import Q

from core.db.mixins import TimeStampedModel, UserScopedModel


class LeaveRequest(TimeStampedModel, UserScopedModel):
    """An employee's leave application."""

    LEAVE_TYPES = [
        ("CL", "Casual Leave"),
        ("RH", "Restricted Holiday"),
        ("SCL", "Special Casual Leave"),
        ("EL", "Earned Leave"),
        ("COL", "Commuted Leave"),
        ("VL", "Vacation Leave"),
    ]

    HALF_DAY_PERIODS = [
        ("first", "First Half"),
        ("second", "Second Half"),
    ]

    STATUSES = [
        ("draft", "Draft"),
        ("pending_substitute", "Pending Substitute"),
        ("pending_unit_head", "Pending Unit Head"),
        ("pending_sanction", "Pending Sanction"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("withdrawn", "Withdrawn"),
        ("pending_cancellation", "Pending Cancellation"),
        ("cancelled", "Cancelled"),
    ]

    leave_type = models.CharField(max_length=3, choices=LEAVE_TYPES)
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField()

    half_day = models.BooleanField(default=False)
    half_day_period = models.CharField(
        max_length=6,
        choices=HALF_DAY_PERIODS,
        blank=True,
    )

    # Station Leave is part of this application, not a separate leave request.
    station_leave_required = models.BooleanField(default=False)
    station_destination = models.CharField(max_length=200, blank=True)
    station_departure_at = models.DateTimeField(null=True, blank=True)
    station_return_at = models.DateTimeField(null=True, blank=True)

    substitute_user_id = models.IntegerField(null=True, blank=True)
    substitute_status = models.CharField(
        max_length=12,
        choices=[
            ("not_required", "Not Required"),
            ("pending", "Pending"),
            ("accepted", "Accepted"),
            ("declined", "Declined"),
        ],
        default="not_required",
    )
    substitute_responded_at = models.DateTimeField(null=True, blank=True)

    status = models.CharField(
        max_length=24,
        choices=STATUSES,
        default="draft",
        db_index=True,
    )

    submitted_at = models.DateTimeField(null=True, blank=True)
    final_decided_at = models.DateTimeField(null=True, blank=True)
    final_decided_by_user_id = models.IntegerField(null=True, blank=True)

    # Optimistic concurrency field for safe state transitions.
    version = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "elm_leave_request"
        constraints = [
            models.CheckConstraint(
                condition=Q(end_date__gte=models.F("start_date")),
                name="elm_request_dates_valid",
            ),
            models.CheckConstraint(
                condition=(
                    Q(half_day=False, half_day_period="")
                    | (
                        Q(half_day=True)
                        & Q(leave_type="CL")
                        & Q(start_date=models.F("end_date"))
                        & Q(half_day_period__in=["first", "second"])
                    )
                ),
                name="elm_request_half_day_valid",
            ),
            models.CheckConstraint(
                condition=(
                    Q(station_leave_required=False)
                    | (
                        Q(station_destination__gt="")
                        & Q(station_departure_at__isnull=False)
                        & Q(station_return_at__isnull=False)
                    )
                ),
                name="elm_station_leave_details_valid",
            ),
        ]
        indexes = [
            models.Index(
                fields=["user_id", "status"],
                name="elm_request_user_status_idx",
            ),
            models.Index(
                fields=["start_date", "end_date"],
                name="elm_request_dates_idx",
            ),
        ]
        ordering = ["-created_at"]

    @property
    def total_calendar_days(self):
        return (self.end_date - self.start_date).days + 1

    def __str__(self):
        return (
            f"ELM-{self.pk or 'new'} u{self.user_id} "
            f"{self.leave_type} {self.start_date}–{self.end_date}"
        )


class LeaveAttachment(TimeStampedModel):
    """Supporting evidence attached to a leave request."""

    request = models.ForeignKey(
        LeaveRequest,
        on_delete=models.CASCADE,
        related_name="attachments",
    )
    attachment_type = models.CharField(
        max_length=20,
        choices=[
            ("medical", "Medical Evidence"),
            ("supporting", "Supporting Document"),
            ("other", "Other"),
        ],
    )
    title = models.CharField(max_length=160, blank=True)
    file_url = models.URLField(max_length=500)
    uploaded_by_user_id = models.IntegerField()

    class Meta:
        db_table = "elm_leave_attachment"
        ordering = ["created_at"]

    def __str__(self):
        return self.title or f"{self.attachment_type} attachment"

