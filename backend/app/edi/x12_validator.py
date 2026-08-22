from backend.app.edi.exceptions import EDIValidationError


def validate_purchase_order(
    purchase_order: dict[str, object],
) -> None:
    po_number = purchase_order.get(
        "purchase_order_number"
    )

    if not po_number:
        raise EDIValidationError(
            "Purchase order number is required"
        )


def validate_item(
    quantity: float,
    unit_price: float,
) -> None:
    if quantity <= 0:
        raise EDIValidationError(
            "Item quantity must be greater than zero"
        )

    if unit_price < 0:
        raise EDIValidationError(
            "Item unit price cannot be negative"
        )