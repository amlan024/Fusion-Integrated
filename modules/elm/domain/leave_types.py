"""Supported leave categories for Employee Leave Management."""

CL = "CL"
RH = "RH"
SCL = "SCL"
EL = "EL"
VL = "VL"
COL = "COL"

LEAVE_TYPES = (
    (CL, "Casual Leave"),
    (RH, "Restricted Holiday"),
    (SCL, "Special Casual Leave"),
    (EL, "Earned Leave"),
    (VL, "Vacation Leave"),
    (COL, "Commuted Leave"),
)

LEAVE_TYPE_CODES = frozenset(code for code, _ in LEAVE_TYPES)


def is_supported_leave_type(leave_type: str) -> bool:
    """Return whether a leave category is supported."""
    return leave_type in LEAVE_TYPE_CODES
