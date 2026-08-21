from datetime import datetime

from backend.app.erp.schemas import ERPPurchaseOrder


_failure_attempts: dict[str, int] = {}


def create_erp_purchase_order(
    purchase_order: ERPPurchaseOrder,
) -> dict[str, object]:
    po_number = purchase_order.purchase_order_number

    if po_number == "PO-FAIL-PERM-005":
        raise RuntimeError(
            "Simulated permanent ERP service failure"
        )

    if po_number == "PO-RETRY-001":
        current_attempt = _failure_attempts.get(po_number, 0) + 1
        _failure_attempts[po_number] = current_attempt

        if current_attempt < 3:
            raise RuntimeError(
                f"Simulated ERP service failure on attempt {current_attempt}"
            )

    erp_order_number = f"ERP-{po_number}"

    return {
        "status": "created",
        "erp_order_number": erp_order_number,
        "purchase_order_number": po_number,
        "created_at": datetime.now().isoformat(),
    }