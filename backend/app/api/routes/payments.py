from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.auth_deps import require_roles
from app.api.deps import get_db
from app.models.auth import User, UserRole
from app.schemas.orders import (
    OrderRead,
    RazorpayPaymentStart,
    RazorpayPaymentStartRead,
    RazorpayPaymentVerification,
)
from app.services import razorpay as razorpay_service


router = APIRouter(prefix="/payments/razorpay", tags=["payments"])


@router.post("/orders", response_model=RazorpayPaymentStartRead, status_code=201)
def start_razorpay_payment(
    payment_in: RazorpayPaymentStart,
    db: Session = Depends(get_db),
    buyer: User = Depends(require_roles(UserRole.BUYER)),
) -> dict:
    return razorpay_service.start_payment(db, buyer.id, payment_in)


@router.post("/verify", response_model=OrderRead)
def verify_razorpay_payment(
    payment_in: RazorpayPaymentVerification,
    db: Session = Depends(get_db),
    buyer: User = Depends(require_roles(UserRole.BUYER)),
) -> OrderRead:
    return razorpay_service.verify_payment(
        db, buyer.id, payment_in.razorpay_order_id,
        payment_in.razorpay_payment_id, payment_in.razorpay_signature,
    )


@router.post("/orders/{order_id}/cancel", response_model=OrderRead)
def cancel_razorpay_payment(
    order_id: int,
    db: Session = Depends(get_db),
    buyer: User = Depends(require_roles(UserRole.BUYER)),
) -> OrderRead:
    return razorpay_service.cancel_pending_payment(db, buyer.id, order_id)
