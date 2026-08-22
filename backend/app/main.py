import logging

from fastapi import (
    Depends,
    FastAPI,
    File,
    HTTPException,
    UploadFile,
)
from fastapi.responses import PlainTextResponse
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    generate_latest,
)
from sqlalchemy.exc import IntegrityError

from backend.app.core.logging_config import setup_logging
from backend.app.core.metrics import (
    api_requests_total,
    edi_completed_total,
    edi_failed_total,
    edi_rejected_total,
)
from backend.app.core.security import verify_api_key
from backend.app.db import models
from backend.app.db.database import (
    Base,
    SessionLocal,
    engine,
)
from backend.app.db.service import (
    create_edi_transaction,
    get_edi_transactions,
    get_transaction_by_control_number,
    get_transaction_by_po_number,
)
from backend.app.edi.exceptions import EDIValidationError
from backend.app.edi.x12_parser import (
    parse_purchase_order,
    parse_purchase_order_text,
)
from backend.app.erp.router import router as erp_router
from backend.app.erp.schemas import ERPPurchaseOrder
from backend.app.erp.service import create_erp_purchase_order


Base.metadata.create_all(bind=engine)

setup_logging()

logger = logging.getLogger(__name__)


app = FastAPI(
    title="EDIFlow Canada",
    description="B2B EDI and ERP Integration Platform",
    version="0.1.0",
)

app.include_router(erp_router)


@app.get("/")
def home() -> dict[str, str]:
    return {
        "message": "Welcome to EDIFlow Canada",
        "status": "running",
    }


@app.get("/health")
def health_check() -> dict[str, str]:
    return {
        "status": "healthy",
        "service": "ediflow-canada",
    }


@app.get("/metrics")
def metrics() -> PlainTextResponse:
    api_requests_total.inc()

    return PlainTextResponse(
        generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )


@app.get("/api/edi/transactions")
def list_edi_transactions() -> list[dict[str, object]]:
    db = SessionLocal()

    try:
        transactions = get_edi_transactions(db)

        return [
            {
                "id": transaction.id,
                "filename": transaction.filename,
                "status": transaction.status,
                "control_number": transaction.control_number,
                "purchase_order_number": (
                    transaction.purchase_order_number
                ),
                "erp_order_number": (
                    transaction.erp_order_number
                ),
                "error_message": (
                    transaction.error_message
                ),
                "created_at": (
                    transaction.created_at.isoformat()
                ),
            }
            for transaction in transactions
        ]

    finally:
        db.close()


@app.get("/api/edi/sample")
def parse_sample_purchase_order() -> dict[str, object]:
    file_path = (
        "edi_samples/x12/missing_po_number_850.txt"
    )

    try:
        return parse_purchase_order(file_path)

    except EDIValidationError as error:
        raise HTTPException(
            status_code=400,
            detail={
                "status": "rejected",
                "error": str(error),
            },
        ) from error


@app.post("/api/edi/upload")
async def upload_edi_file(
    file: UploadFile = File(...),
    _: None = Depends(verify_api_key),
) -> dict[str, object]:
    db = SessionLocal()

    try:
        if (
            not file.filename
            or not file.filename.endswith(".txt")
        ):
            raise HTTPException(
                status_code=400,
                detail="Only .txt EDI files are allowed",
            )

        content = await file.read()

        try:
            raw_edi = content.decode("utf-8")

        except UnicodeDecodeError as error:
            raise HTTPException(
                status_code=400,
                detail=(
                    "The uploaded file must use "
                    "UTF-8 encoding"
                ),
            ) from error

        purchase_order = parse_purchase_order_text(
            raw_edi
        )

        existing_control_transaction = (
            get_transaction_by_control_number(
                db=db,
                control_number=str(
                    purchase_order["control_number"]
                ),
            )
        )

        if existing_control_transaction:
            logger.warning(
                (
                    "Duplicate EDI control number | "
                    "filename=%s | control_number=%s"
                ),
                file.filename,
                purchase_order["control_number"],
            )

            raise HTTPException(
                status_code=409,
                detail={
                    "status": "duplicate",
                    "error": (
                        "EDI control number "
                        "already processed"
                    ),
                    "existing_transaction_id": (
                        existing_control_transaction.id
                    ),
                },
            )

        existing_po_transaction = (
            get_transaction_by_po_number(
                db=db,
                purchase_order_number=str(
                    purchase_order[
                        "purchase_order_number"
                    ]
                ),
            )
        )

        if existing_po_transaction:
            logger.warning(
                (
                    "Duplicate purchase order | "
                    "filename=%s | po_number=%s"
                ),
                file.filename,
                purchase_order[
                    "purchase_order_number"
                ],
            )

            raise HTTPException(
                status_code=409,
                detail={
                    "status": "duplicate",
                    "error": (
                        "Purchase order "
                        "already processed"
                    ),
                    "existing_transaction_id": (
                        existing_po_transaction.id
                    ),
                },
            )

        erp_purchase_order = ERPPurchaseOrder(
            purchase_order_number=str(
                purchase_order[
                    "purchase_order_number"
                ]
            ),
            order_date=str(
                purchase_order["order_date"]
            ),
            currency=str(
                purchase_order["currency"]
            ),
            buyer=purchase_order["buyer"],
            supplier=purchase_order["supplier"],
            items=purchase_order["items"],
        )

        max_attempts = 3
        erp_response = None

        for attempt in range(
            1,
            max_attempts + 1,
        ):
            try:
                erp_response = (
                    create_erp_purchase_order(
                        erp_purchase_order
                    )
                )

                logger.info(
                    (
                        "ERP request succeeded | "
                        "po_number=%s | attempt=%s"
                    ),
                    purchase_order[
                        "purchase_order_number"
                    ],
                    attempt,
                )

                break

            except RuntimeError as error:
                logger.warning(
                    (
                        "ERP request failed | "
                        "po_number=%s | "
                        "attempt=%s | error=%s"
                    ),
                    purchase_order[
                        "purchase_order_number"
                    ],
                    attempt,
                    str(error),
                )

                if attempt == max_attempts:
                    raise

        if erp_response is None:
            raise RuntimeError(
                "ERP service did not return a response"
            )

        transaction = create_edi_transaction(
            db=db,
            filename=file.filename,
            status="completed",
            control_number=str(
                purchase_order["control_number"]
            ),
            purchase_order_number=str(
                purchase_order[
                    "purchase_order_number"
                ]
            ),
            erp_order_number=str(
                erp_response["erp_order_number"]
            ),
        )

        edi_completed_total.inc()

        logger.info(
            (
                "EDI transaction completed | "
                "filename=%s | "
                "control_number=%s | "
                "po_number=%s | "
                "erp_order=%s"
            ),
            file.filename,
            purchase_order["control_number"],
            purchase_order[
                "purchase_order_number"
            ],
            erp_response["erp_order_number"],
        )

        return {
            "filename": file.filename,
            "status": "completed",
            "transaction_id": transaction.id,
            "purchase_order": purchase_order,
            "erp_response": erp_response,
        }

    except RuntimeError as error:
        edi_failed_total.inc()

        logger.error(
            (
                "ERP service failure | "
                "filename=%s | error=%s"
            ),
            file.filename,
            str(error),
        )

        create_edi_transaction(
            db=db,
            filename=file.filename or "unknown",
            status="failed",
            control_number=str(
                purchase_order["control_number"]
            ),
            purchase_order_number=str(
                purchase_order[
                    "purchase_order_number"
                ]
            ),
            error_message=str(error),
        )

        raise HTTPException(
            status_code=502,
            detail={
                "status": "failed",
                "error": "ERP service unavailable",
            },
        ) from error

    except IntegrityError as error:
        db.rollback()

        logger.error(
            (
                "Database duplicate blocked | "
                "filename=%s"
            ),
            file.filename,
        )

        raise HTTPException(
            status_code=409,
            detail={
                "status": "duplicate",
                "error": (
                    "Duplicate transaction "
                    "blocked by database"
                ),
            },
        ) from error

    except EDIValidationError as error:
        edi_rejected_total.inc()

        create_edi_transaction(
            db=db,
            filename=file.filename or "unknown",
            status="rejected",
            error_message=str(error),
        )

        logger.warning(
            (
                "EDI validation rejected | "
                "filename=%s | error=%s"
            ),
            file.filename,
            str(error),
        )

        raise HTTPException(
            status_code=400,
            detail={
                "status": "rejected",
                "error": str(error),
            },
        ) from error

    finally:
        db.close()