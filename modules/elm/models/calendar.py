
"""Published holiday and Restricted Holiday calendar."""

from django.db import models
from django.db.models import Q

from core.db.mixins import TimeStampedModel


class LeaveCalendar(TimeStampedModel):
    """A calendar becomes effective only after it is published."""

    name = models.CharField(max_length=120)
    calendar_year = models.PositiveSmallIntegerField(db_index=True)
    is_published = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)
    published_by_user_id = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "elm_leave_calendar"
        constraints = [
            models.UniqueConstraint(
                fields=["calendar_year"],
                condition=Q(is_published=True),
                name="elm_one_published_calendar_per_year",
            ),
        ]
        ordering = ["-calendar_year", "name"]

    def __str__(self):
        status = "published" if self.is_published else "unpublished"
        return f"{self.name} ({self.calendar_year}, {status})"


class CalendarDay(TimeStampedModel):
    """A public holiday, closed day or Restricted Holiday date."""

    DAY_TYPES = [
        ("public", "Public Holiday"),
        ("restricted", "Restricted Holiday"),
        ("closed", "Other Closed Day"),
    ]

    calendar = models.ForeignKey(
        LeaveCalendar,
        on_delete=models.CASCADE,
        related_name="days",
    )
    date = models.DateField()
    title = models.CharField(max_length=160)
    day_type = models.CharField(max_length=12, choices=DAY_TYPES)
    is_closed = models.BooleanField(default=True)

    class Meta:
        db_table = "elm_calendar_day"
        constraints = [
            models.UniqueConstraint(
                fields=["calendar", "date", "title"],
                name="elm_calendar_day_unique",
            ),
        ]
        indexes = [
            models.Index(
                fields=["date", "day_type"],
                name="elm_calendar_date_type_idx",
            ),
        ]
        ordering = ["date", "title"]

    def __str__(self):
        return f"{self.date}: {self.title}"

