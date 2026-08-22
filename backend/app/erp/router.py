from fastapi import APIRouter, HTTPException

from backend.app.erp.schemas import ERPPurchaseOrder
from backend.app.erp.service import (
    create_erp_purchase_order,
    get_erp_failure_mode,
    set_erp_failure_mode,
)


router = APIRouter(
    prefix="/api/erp",
    tags=["ERP"],
)


@router.post("/purchase-orders")
def create_purchase_order(
    purchase_order: ERPPurchaseOrder,
) -> dict[str, object]:
    return create_erp_purchase_order(
        purchase_order
    )


@router.get("/simulation-mode")
def read_simulation_mode() -> dict[str, str]:
    return {
        "mode": get_erp_failure_mode()
    }


@router.post("/simulation-mode/{mode}")
def change_simulation_mode(
    mode: str,
) -> dict[str, str]:
    try:
        updated_mode = set_erp_failure_mode(
            mode
        )

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error

    return {
        "mode": updated_mode
    }