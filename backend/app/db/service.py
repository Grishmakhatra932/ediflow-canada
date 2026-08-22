from sqlalchemy.orm import Session

from backend.app.db.models import EDITransaction


def create_edi_transaction(
    db: Session,
    filename: str,
    status: str,
    control_number: str | None = None,
    purchase_order_number: str | None = None,
    erp_order_number: str | None = None,
    error_message: str | None = None,
) -> EDITransaction:
    transaction = EDITransaction(
        filename=filename,
        status=status,
        control_number=control_number,
        purchase_order_number=purchase_order_number,
        erp_order_number=erp_order_number,
        error_message=error_message,
    )

    db.add(transaction)
    db.commit()
    db.refresh(transaction)

    return transaction


def get_edi_transactions(
    db: Session,
) -> list[EDITransaction]:
    return (
        db.query(EDITransaction)
        .order_by(EDITransaction.id.desc())
        .all()
    )


def get_transaction_by_po_number(
    db: Session,
    purchase_order_number: str,
) -> EDITransaction | None:
    return (
        db.query(EDITransaction)
        .filter(
            EDITransaction.purchase_order_number
            == purchase_order_number
        )
        .first()
    )


def get_transaction_by_control_number(
    db: Session,
    control_number: str,
) -> EDITransaction | None:
    return (
        db.query(EDITransaction)
        .filter(
            EDITransaction.control_number
            == control_number
        )
        .first()
    )