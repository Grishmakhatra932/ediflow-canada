from fastapi import APIRouter

from backend.app.erp.schemas import ERPPurchaseOrder
from backend.app.erp.service import create_erp_purchase_order


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