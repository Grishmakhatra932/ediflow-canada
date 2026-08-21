from datetime import datetime
from pathlib import Path

from backend.app.edi.exceptions import EDIValidationError
from backend.app.edi.x12_validator import (
    validate_item,
    validate_purchase_order,
)


def read_x12_file(file_path: str) -> str:
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(
            f"EDI file not found: {file_path}"
        )

    return path.read_text(
        encoding="utf-8"
    ).strip()


def split_segments(
    raw_edi: str,
) -> list[list[str]]:
    segments: list[list[str]] = []

    for raw_segment in raw_edi.split("~"):
        cleaned_segment = raw_segment.strip()

        if cleaned_segment:
            segments.append(
                cleaned_segment.split("*")
            )

    return segments


def get_purchase_order_number(
    segments: list[list[str]],
) -> str:
    for segment in segments:
        if segment[0] == "BEG":
            if len(segment) <= 3:
                raise EDIValidationError(
                    "BEG segment is incomplete"
                )

            purchase_order_number = (
                segment[3].strip()
            )

            if not purchase_order_number:
                raise EDIValidationError(
                    "Purchase order number is missing"
                )

            return purchase_order_number

    raise EDIValidationError(
        "BEG segment not found"
    )


def get_order_date(
    segments: list[list[str]],
) -> str:
    for segment in segments:
        if segment[0] == "BEG":
            if len(segment) <= 5:
                raise EDIValidationError(
                    "BEG order date is missing"
                )

            raw_date = segment[5].strip()

            if not raw_date:
                raise EDIValidationError(
                    "BEG order date is missing"
                )

            try:
                parsed_date = datetime.strptime(
                    raw_date,
                    "%Y%m%d",
                )

            except ValueError as error:
                raise EDIValidationError(
                    "BEG order date is invalid"
                ) from error

            return parsed_date.strftime(
                "%Y-%m-%d"
            )

    raise EDIValidationError(
        "BEG segment not found"
    )


def get_control_number(
    segments: list[list[str]],
) -> str:
    for segment in segments:
        if segment[0] == "ISA":
            if len(segment) <= 13:
                raise EDIValidationError(
                    "ISA segment is incomplete"
                )

            control_number = (
                segment[13].strip()
            )

            if not control_number:
                raise EDIValidationError(
                    "EDI control number is missing"
                )

            return control_number

    raise EDIValidationError(
        "ISA segment not found"
    )


def get_buyer(
    segments: list[list[str]],
) -> dict[str, str]:
    for segment in segments:
        if (
            len(segment) > 1
            and segment[0] == "N1"
            and segment[1] == "BY"
        ):
            if len(segment) <= 4:
                raise EDIValidationError(
                    "Buyer N1 segment is incomplete"
                )

            buyer_name = segment[2].strip()
            buyer_id = segment[4].strip()

            if not buyer_name:
                raise EDIValidationError(
                    "Buyer name is missing"
                )

            if not buyer_id:
                raise EDIValidationError(
                    "Buyer ID is missing"
                )

            return {
                "name": buyer_name,
                "id": buyer_id,
            }

    raise EDIValidationError(
        "Buyer N1 segment not found"
    )


def get_supplier(
    segments: list[list[str]],
) -> dict[str, str]:
    for segment in segments:
        if (
            len(segment) > 1
            and segment[0] == "N1"
            and segment[1] == "SU"
        ):
            if len(segment) <= 4:
                raise EDIValidationError(
                    "Supplier N1 segment is incomplete"
                )

            supplier_name = (
                segment[2].strip()
            )
            supplier_id = (
                segment[4].strip()
            )

            if not supplier_name:
                raise EDIValidationError(
                    "Supplier name is missing"
                )

            if not supplier_id:
                raise EDIValidationError(
                    "Supplier ID is missing"
                )

            return {
                "name": supplier_name,
                "id": supplier_id,
            }

    raise EDIValidationError(
        "Supplier N1 segment not found"
    )


def get_items(
    segments: list[list[str]],
) -> list[dict[str, object]]:
    items: list[dict[str, object]] = []

    for segment in segments:
        if segment[0] == "PO1":
            if len(segment) <= 7:
                raise EDIValidationError(
                    "PO1 segment is incomplete"
                )

            try:
                line_number = int(segment[1])
                quantity = float(segment[2])
                unit_price = float(segment[4])

            except (ValueError, TypeError) as error:
                raise EDIValidationError(
                    "PO1 contains invalid numeric values"
                ) from error

            unit = segment[3].strip()
            sku = segment[7].strip()

            if not unit:
                raise EDIValidationError(
                    "Item unit is missing"
                )

            if not sku:
                raise EDIValidationError(
                    "Item SKU is missing"
                )

            validate_item(
                quantity,
                unit_price,
            )

            items.append(
                {
                    "line_number": line_number,
                    "quantity": quantity,
                    "unit": unit,
                    "unit_price": unit_price,
                    "sku": sku,
                }
            )

    if not items:
        raise EDIValidationError(
            "No PO1 item segments found"
        )

    return items


def parse_purchase_order_text(
    raw_edi: str,
) -> dict[str, object]:
    segments = split_segments(raw_edi)

    if not segments:
        raise EDIValidationError(
            "EDI document is empty"
        )

    purchase_order = {
        "document_type": "PurchaseOrder",
        "control_number": get_control_number(
            segments
        ),
        "purchase_order_number": (
            get_purchase_order_number(
                segments
            )
        ),
        "order_date": get_order_date(
            segments
        ),
        "currency": "CAD",
        "buyer": get_buyer(
            segments
        ),
        "supplier": get_supplier(
            segments
        ),
        "items": get_items(
            segments
        ),
    }

    validate_purchase_order(
        purchase_order
    )

    return purchase_order


def parse_purchase_order(
    file_path: str,
) -> dict[str, object]:
    raw_edi = read_x12_file(
        file_path
    )

    return parse_purchase_order_text(
        raw_edi
    )