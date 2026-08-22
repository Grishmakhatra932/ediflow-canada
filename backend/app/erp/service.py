import os
from datetime import datetime

from backend.app.erp.schemas import ERPPurchaseOrder


_failure_attempts: dict[str, int] = {}

_failure_mode = os.getenv(
    "ERP_FAILURE_MODE",
    "none",
).lower()


def set_erp_failure_mode(mode: str) -> str:
    global _failure_mode

    allowed_modes = {
        "none",
        "retry",
        "permanent",
    }

    normalized_mode = mode.lower()

    if normalized_mode not in allowed_modes:
        raise ValueError(
            "ERP failure mode must be "
            "none, retry, or permanent"
        )

    _failure_mode = normalized_mode

    return _failure_mode


def get_erp_failure_mode() -> str:
    return _failure_mode


def create_erp_purchase_order(
    purchase_order: ERPPurchaseOrder,
) -> dict[str, object]:
    po_number = purchase_order.purchase_order_number

    if _failure_mode == "permanent":
        raise RuntimeError(
            "Simulated permanent ERP service failure"
        )

    if _failure_mode == "retry":
        current_attempt = (
            _failure_attempts.get(po_number, 0) + 1
        )

        _failure_attempts[po_number] = current_attempt

        if current_attempt < 3:
            raise RuntimeError(
                "Simulated ERP service failure "
                f"on attempt {current_attempt}"
            )

    erp_order_number = f"ERP-{po_number}"

    return {
        "status": "created",
        "erp_order_number": erp_order_number,
        "purchase_order_number": po_number,
        "created_at": datetime.now().isoformat(),
    }