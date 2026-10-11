"""Leave balance queries for employees."""

from modules.leave.models import LeaveAccount
from modules.leave.services.authz import require_permission, require_user_id


def list_own_balances(*, actor):
    """Return leave accounts belonging only to the authenticated employee."""
    require_permission(actor, "leave.balance.view_self")
    user_id = require_user_id(actor)

    return LeaveAccount.objects.filter(user_id=user_id).order_by(
        "year", "category"
    )
