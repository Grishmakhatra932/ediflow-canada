from pydantic import BaseModel


class ERPParty(BaseModel):
    id: str
    name: str


class ERPItem(BaseModel):
    line_number: int
    sku: str
    quantity: float
    unit: str
    unit_price: float


class ERPPurchaseOrder(BaseModel):
    purchase_order_number: str
    order_date: str
    currency: str
    buyer: ERPParty
    supplier: ERPParty
    items: list[ERPItem]