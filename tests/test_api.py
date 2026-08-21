import os

from dotenv import load_dotenv
from fastapi.testclient import TestClient

from backend.app.db.database import SessionLocal
from backend.app.db.models import EDITransaction
from backend.app.main import app

load_dotenv()


client = TestClient(app)

API_HEADERS = {
    "X-API-Key": os.environ["API_KEY"],
}


def delete_test_purchase_order(
    purchase_order_number: str,
) -> None:
    db = SessionLocal()

    try:
        db.query(EDITransaction).filter(
            EDITransaction.purchase_order_number
            == purchase_order_number
        ).delete()

        db.commit()

    finally:
        db.close()


def test_health_endpoint() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "service": "ediflow-canada",
    }


def test_valid_edi_upload() -> None:
    delete_test_purchase_order("PO-2026-1001")

    with open(
        "edi_samples/x12/valid_850.txt",
        "rb",
    ) as edi_file:
        response = client.post(
            "/api/edi/upload",
            headers=API_HEADERS,
            files={
                "file": (
                    "valid_850.txt",
                    edi_file,
                    "text/plain",
                )
            },
        )

    response_data = response.json()

    assert response.status_code == 200
    assert response_data["status"] == "completed"
    assert (
        response_data["purchase_order"][
            "purchase_order_number"
        ]
        == "PO-2026-1001"
    )
    assert (
        response_data["erp_response"]["status"]
        == "created"
    )
    assert "transaction_id" in response_data


def test_invalid_quantity_upload() -> None:
    with open(
        "edi_samples/x12/invalid_quantity_850.txt",
        "rb",
    ) as edi_file:
        response = client.post(
            "/api/edi/upload",
            headers=API_HEADERS,
            files={
                "file": (
                    "invalid_quantity_850.txt",
                    edi_file,
                    "text/plain",
                )
            },
        )

    response_data = response.json()

    assert response.status_code == 400
    assert response_data["detail"]["status"] == "rejected"
    assert (
        response_data["detail"]["error"]
        == "Item quantity must be greater than zero"
    )


def test_transaction_history() -> None:
    response = client.get("/api/edi/transactions")

    response_data = response.json()

    assert response.status_code == 200
    assert isinstance(response_data, list)
    assert len(response_data) > 0

    first_transaction = response_data[0]

    assert "id" in first_transaction
    assert "filename" in first_transaction
    assert "status" in first_transaction
    assert "created_at" in first_transaction


def test_erp_purchase_order_creation() -> None:
    purchase_order = {
        "purchase_order_number": "PO-TEST-1001",
        "order_date": "2026-07-30",
        "currency": "CAD",
        "buyer": {
            "id": "BUYER001",
            "name": "Maple Retail Canada",
        },
        "supplier": {
            "id": "SUP1001",
            "name": "NorthStar Foods",
        },
        "items": [
            {
                "line_number": 1,
                "sku": "SKU-9001",
                "quantity": 10,
                "unit": "CA",
                "unit_price": 4.75,
            }
        ],
    }

    response = client.post(
        "/api/erp/purchase-orders",
        json=purchase_order,
    )

    response_data = response.json()

    assert response.status_code == 200
    assert response_data["status"] == "created"
    assert (
        response_data["erp_order_number"]
        == "ERP-PO-TEST-1001"
    )


def test_duplicate_control_number_rejected() -> None:
    delete_test_purchase_order("PO-2026-1001")

    with open(
        "edi_samples/x12/valid_850.txt",
        "rb",
    ) as edi_file:
        first_response = client.post(
            "/api/edi/upload",
            headers=API_HEADERS,
            files={
                "file": (
                    "valid_850.txt",
                    edi_file,
                    "text/plain",
                )
            },
        )

    assert first_response.status_code == 200

    with open(
        "edi_samples/x12/valid_850.txt",
        "rb",
    ) as edi_file:
        duplicate_response = client.post(
            "/api/edi/upload",
            headers=API_HEADERS,
            files={
                "file": (
                    "valid_850.txt",
                    edi_file,
                    "text/plain",
                )
            },
        )

    response_data = duplicate_response.json()

    assert duplicate_response.status_code == 409
    assert response_data["detail"]["status"] == "duplicate"
    assert (
        response_data["detail"]["error"]
        == "EDI control number already processed"
    )
    assert (
        "existing_transaction_id"
        in response_data["detail"]
    )


def test_erp_retry_succeeds_on_third_attempt() -> None:
    delete_test_purchase_order("PO-RETRY-001")

    file_path = "edi_samples/x12/erp_failure_850.txt"

    with open(file_path, "rb") as edi_file:
        response = client.post(
            "/api/edi/upload",
            headers=API_HEADERS,
            files={
                "file": (
                    "erp_failure_850.txt",
                    edi_file,
                    "text/plain",
                )
            },
        )

    assert response.status_code == 200

    response_data = response.json()

    assert response_data["status"] == "completed"
    assert (
        response_data["purchase_order"][
            "purchase_order_number"
        ]
        == "PO-RETRY-001"
    )
    assert (
        response_data["erp_response"]["erp_order_number"]
        == "ERP-PO-RETRY-001"
    )

def test_upload_without_api_key_returns_401() -> None:
    with open(
        "edi_samples/x12/valid_850.txt",
        "rb",
    ) as edi_file:
        response = client.post(
            "/api/edi/upload",
            files={
                "file": (
                    "valid_850.txt",
                    edi_file,
                    "text/plain",
                )
            },
        )

    response_data = response.json()

    assert response.status_code == 401
    assert (
        response_data["detail"]
        == "Invalid or missing API key"
    )

def test_missing_isa_segment_returns_400() -> None:
    with open(
        "edi_samples/x12/missing_isa_850.txt",
        "rb",
    ) as edi_file:
        response = client.post(
            "/api/edi/upload",
            headers=API_HEADERS,
            files={
                "file": (
                    "missing_isa_850.txt",
                    edi_file,
                    "text/plain",
                )
            },
        )

    response_data = response.json()

    assert response.status_code == 400
    assert response_data["detail"]["status"] == "rejected"
    assert (
        response_data["detail"]["error"]
        == "ISA segment not found"
    )

def test_incomplete_isa_segment_returns_400() -> None:
    with open(
        "edi_samples/x12/incomplete_isa_850.txt",
        "rb",
    ) as edi_file:
        response = client.post(
            "/api/edi/upload",
            headers=API_HEADERS,
            files={
                "file": (
                    "incomplete_isa_850.txt",
                    edi_file,
                    "text/plain",
                )
            },
        )

    response_data = response.json()

    assert response.status_code == 400
    assert response_data["detail"]["status"] == "rejected"
    assert (
        response_data["detail"]["error"]
        == "ISA segment is incomplete"
    )

def test_missing_control_number_returns_400() -> None:
    with open(
        "edi_samples/x12/missing_control_number_850.txt",
        "rb",
    ) as edi_file:
        response = client.post(
            "/api/edi/upload",
            headers=API_HEADERS,
            files={
                "file": (
                    "missing_control_number_850.txt",
                    edi_file,
                    "text/plain",
                )
            },
        )

    response_data = response.json()

    assert response.status_code == 400
    assert response_data["detail"]["status"] == "rejected"
    assert (
        response_data["detail"]["error"]
        == "EDI control number is missing"
    )

def test_missing_beg_segment_returns_400() -> None:
    with open(
        "edi_samples/x12/missing_beg_850.txt",
        "rb",
    ) as edi_file:
        response = client.post(
            "/api/edi/upload",
            headers=API_HEADERS,
            files={
                "file": (
                    "missing_beg_850.txt",
                    edi_file,
                    "text/plain",
                )
            },
        )

    response_data = response.json()

    assert response.status_code == 400
    assert response_data["detail"]["status"] == "rejected"
    assert (
        response_data["detail"]["error"]
        == "BEG segment not found"
    )

def test_missing_po_number_in_beg_returns_400() -> None:
    with open(
        "edi_samples/x12/missing_po_number_in_beg_850.txt",
        "rb",
    ) as edi_file:
        response = client.post(
            "/api/edi/upload",
            headers=API_HEADERS,
            files={
                "file": (
                    "missing_po_number_in_beg_850.txt",
                    edi_file,
                    "text/plain",
                )
            },
        )

    response_data = response.json()

    assert response.status_code == 400
    assert response_data["detail"]["status"] == "rejected"
    assert (
        response_data["detail"]["error"]
        == "Purchase order number is missing"
    )

def test_incomplete_beg_segment_returns_400() -> None:
    with open(
        "edi_samples/x12/incomplete_beg_850.txt",
        "rb",
    ) as edi_file:
        response = client.post(
            "/api/edi/upload",
            headers=API_HEADERS,
            files={
                "file": (
                    "incomplete_beg_850.txt",
                    edi_file,
                    "text/plain",
                )
            },
        )

    response_data = response.json()

    assert response.status_code == 400
    assert response_data["detail"]["status"] == "rejected"
    assert (
        response_data["detail"]["error"]
        == "BEG segment is incomplete"
    )

def test_missing_order_date_returns_400() -> None:
    with open(
        "edi_samples/x12/missing_order_date_850.txt",
        "rb",
    ) as edi_file:
        response = client.post(
            "/api/edi/upload",
            headers=API_HEADERS,
            files={
                "file": (
                    "missing_order_date_850.txt",
                    edi_file,
                    "text/plain",
                )
            },
        )

    response_data = response.json()

    assert response.status_code == 400
    assert response_data["detail"]["status"] == "rejected"
    assert (
        response_data["detail"]["error"]
        == "BEG order date is missing"
    )

def test_invalid_order_date_returns_400() -> None:
    with open(
        "edi_samples/x12/invalid_order_date_850.txt",
        "rb",
    ) as edi_file:
        response = client.post(
            "/api/edi/upload",
            headers=API_HEADERS,
            files={
                "file": (
                    "invalid_order_date_850.txt",
                    edi_file,
                    "text/plain",
                )
            },
        )

    response_data = response.json()

    assert response.status_code == 400
    assert response_data["detail"]["status"] == "rejected"
    assert (
        response_data["detail"]["error"]
        == "BEG order date is invalid"
    )

def test_missing_buyer_returns_400() -> None:
    with open(
        "edi_samples/x12/missing_buyer_850.txt",
        "rb",
    ) as edi_file:
        response = client.post(
            "/api/edi/upload",
            headers=API_HEADERS,
            files={
                "file": (
                    "missing_buyer_850.txt",
                    edi_file,
                    "text/plain",
                )
            },
        )

    response_data = response.json()

    assert response.status_code == 400
    assert response_data["detail"]["status"] == "rejected"
    assert (
        response_data["detail"]["error"]
        == "Buyer N1 segment not found"
    )

def test_missing_supplier_returns_400() -> None:
    with open(
        "edi_samples/x12/missing_supplier_850.txt",
        "rb",
    ) as edi_file:
        response = client.post(
            "/api/edi/upload",
            headers=API_HEADERS,
            files={
                "file": (
                    "missing_supplier_850.txt",
                    edi_file,
                    "text/plain",
                )
            },
        )

    response_data = response.json()

    assert response.status_code == 400
    assert response_data["detail"]["status"] == "rejected"
    assert (
        response_data["detail"]["error"]
        == "Supplier N1 segment not found"
    )

def test_missing_po1_returns_400() -> None:
    with open(
        "edi_samples/x12/missing_po1_850.txt",
        "rb",
    ) as edi_file:
        response = client.post(
            "/api/edi/upload",
            headers=API_HEADERS,
            files={
                "file": (
                    "missing_po1_850.txt",
                    edi_file,
                    "text/plain",
                )
            },
        )

    response_data = response.json()

    assert response.status_code == 400
    assert response_data["detail"]["status"] == "rejected"
    assert (
        response_data["detail"]["error"]
        == "No PO1 item segments found"
    )

def test_missing_sku_returns_400() -> None:
    with open(
        "edi_samples/x12/missing_sku_850.txt",
        "rb",
    ) as edi_file:
        response = client.post(
            "/api/edi/upload",
            headers=API_HEADERS,
            files={
                "file": (
                    "missing_sku_850.txt",
                    edi_file,
                    "text/plain",
                )
            },
        )

    response_data = response.json()

    assert response.status_code == 400
    assert response_data["detail"]["status"] == "rejected"
    assert (
        response_data["detail"]["error"]
        == "Item SKU is missing"
    )

def test_invalid_unit_price_format_returns_400() -> None:
    with open(
        "edi_samples/x12/invalid_unit_price_format_850.txt",
        "rb",
    ) as edi_file:
        response = client.post(
            "/api/edi/upload",
            headers=API_HEADERS,
            files={
                "file": (
                    "invalid_unit_price_format_850.txt",
                    edi_file,
                    "text/plain",
                )
            },
        )

    response_data = response.json()

    assert response.status_code == 400
    assert response_data["detail"]["status"] == "rejected"
    assert (
        response_data["detail"]["error"]
        == "PO1 contains invalid numeric values"
    )

def test_wrong_file_extension_returns_400() -> None:
    response = client.post(
        "/api/edi/upload",
        headers=API_HEADERS,
        files={
            "file": (
                "sample.pdf",
                b"not-an-edi-file",
                "application/pdf",
            )
        },
    )

    response_data = response.json()

    assert response.status_code == 400
    assert (
        response_data["detail"]
        == "Only .txt EDI files are allowed"
    )

def test_non_utf8_file_returns_400() -> None:
    response = client.post(
        "/api/edi/upload",
        headers=API_HEADERS,
        files={
            "file": (
                "non_utf8_850.txt",
                bytes([0xFF, 0xFE, 0xFD]),
                "text/plain",
            )
        },
    )

    response_data = response.json()

    assert response.status_code == 400
    assert (
        response_data["detail"]
        == "The uploaded file must use UTF-8 encoding"
    )

def test_missing_unit_returns_400() -> None:
    with open(
        "edi_samples/x12/missing_unit_850.txt",
        "rb",
    ) as edi_file:
        response = client.post(
            "/api/edi/upload",
            headers=API_HEADERS,
            files={
                "file": (
                    "missing_unit_850.txt",
                    edi_file,
                    "text/plain",
                )
            },
        )

    response_data = response.json()

    assert response.status_code == 400
    assert response_data["detail"]["status"] == "rejected"
    assert (
        response_data["detail"]["error"]
        == "Item unit is missing"
    )