
"""Permissions recognised by Employee Leave Management."""

PERMISSIONS = [
    ("leave.application.view_self", "View own leave applications"),
    ("leave.application.create", "Submit a leave application"),
    ("leave.application.withdraw", "Withdraw a pending application"),
    ("leave.application.review", "Review leave applications"),
    ("leave.application.decide", "Make final leave decisions"),
    ("leave.balance.view_self", "View own leave balances"),
    ("leave.policy.manage", "Manage leave policy"),
    ("leave.calendar.manage", "Manage holiday and RH calendars"),
    ("leave.record.manage", "Record previously sanctioned leave"),
    ("leave.report.view", "View leave reports"),
]

SYSTEM_PERMISSIONS = [
    "leave.workflow.remind",
    "leave.workflow.escalate",
    "leave.year_end.process",
]

PERMISSIONS.extend([
    ("leave.workflow.remind", "Send workflow reminders"),
    ("leave.workflow.escalate", "Escalate overdue workflow tasks"),
    ("leave.year_end.process", "Process year-end leave balances"),
])

_EMPLOYEE = [
    "leave.application.view_self",
    "leave.application.create",
    "leave.application.withdraw",
    "leave.balance.view_self",
]

_LEAVE_ADMIN = [
    "leave.application.review",
    "leave.application.decide",
    "leave.policy.manage",
    "leave.calendar.manage",
    "leave.record.manage",
    "leave.report.view",
]

ROLE_GRANTS = {
    "employee": _EMPLOYEE,
    "faculty": _EMPLOYEE,
    "staff": _EMPLOYEE,
    "leave_administrator": _LEAVE_ADMIN,
}
