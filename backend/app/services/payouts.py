from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.auth import User, UserRole
from app.models.order import Order, OrderItem
from app.models.seller_payout import SellerPayout
from app.schemas.payouts import (
    AdminPayoutDashboardRead,
    AdminPayoutRead,
    AdminSellerEarningsRead,
    PayoutCreate,
    PayoutStatus,
    PayoutUpdate,
    SellerEarningsRead,
)

CENT = Decimal("0.01")
RESERVED_STATUSES = {PayoutStatus.PENDING.value, PayoutStatus.PROCESSING.value, PayoutStatus.PAID.value}
NEXT_STATUSES = {
    PayoutStatus.PENDING: {PayoutStatus.PROCESSING, PayoutStatus.PAID, PayoutStatus.FAILED},
    PayoutStatus.PROCESSING: {PayoutStatus.PAID, PayoutStatus.FAILED},
    PayoutStatus.PAID: set(),
    PayoutStatus.FAILED: set(),
}


def _seller_earnings(db: Session, seller_id: int) -> SellerEarningsRead:
    rows = db.execute(
        select(
            Order.id,
            Order.status,
            Order.payment_method,
            Order.payment_status,
            Order.subtotal,
            Order.discount_amount,
            OrderItem.quantity,
            OrderItem.line_total,
        )
        .join(OrderItem, OrderItem.order_id == Order.id)
        .where(OrderItem.seller_id == seller_id)
        .order_by(Order.id)
    ).all()
    orders: dict[int, dict] = {}
    total_sales = 0
    for order_id, order_status, payment_method, payment_status, subtotal, discount, quantity, line_total in rows:
        if order_status == "cancelled":
            continue
        total_sales += quantity
        entry = orders.setdefault(order_id, {
            "status": order_status,
            "payment_method": payment_method,
            "payment_status": payment_status,
            "subtotal": subtotal or Decimal("0.00"),
            "discount": discount or Decimal("0.00"),
            "seller_gross": Decimal("0.00"),
        })
        entry["seller_gross"] += line_total

    earnings = Decimal("0.00")
    gross_sales = sum((order["seller_gross"] for order in orders.values()), Decimal("0.00"))
    eligible_earnings = Decimal("0.00")
    for order in orders.values():
        gross = order["seller_gross"]
        order_subtotal = order["subtotal"]
        allocated_discount = (
            (order["discount"] * gross / order_subtotal).quantize(CENT, rounding=ROUND_HALF_UP)
            if order_subtotal > 0 else Decimal("0.00")
        )
        net = max(Decimal("0.00"), gross - allocated_discount).quantize(CENT)
        earnings += net
        is_paid = order["payment_status"] == "paid"
        is_delivered_cod = order["payment_method"] == "cod" and order["status"] == "delivered"
        if is_paid or is_delivered_cod:
            eligible_earnings += net

    payouts = db.execute(
        select(SellerPayout.status, SellerPayout.amount).where(SellerPayout.seller_id == seller_id)
    ).all()
    paid_out = sum((amount for payout_status, amount in payouts if payout_status == PayoutStatus.PAID.value), Decimal("0.00"))
    reserved = sum((amount for payout_status, amount in payouts if payout_status in RESERVED_STATUSES), Decimal("0.00"))
    pending = max(Decimal("0.00"), eligible_earnings - paid_out).quantize(CENT)
    available = max(Decimal("0.00"), eligible_earnings - reserved).quantize(CENT)
    return SellerEarningsRead(
        total_sales=total_sales,
        gross_sales=gross_sales.quantize(CENT),
        earnings=earnings.quantize(CENT),
        eligible_earnings=eligible_earnings.quantize(CENT),
        pending_payments=pending,
        available_for_payout=available,
    )


def seller_payout_history(db: Session, seller_id: int) -> dict:
    payouts = list(db.scalars(
        select(SellerPayout).where(SellerPayout.seller_id == seller_id)
        .order_by(SellerPayout.created_at.desc(), SellerPayout.id.desc())
    ).all())
    return {"earnings": _seller_earnings(db, seller_id), "payouts": payouts}


def admin_payout_dashboard(db: Session) -> AdminPayoutDashboardRead:
    sellers = list(db.scalars(
        select(User).order_by(User.full_name, User.id)
    ).all())
    sellers = [seller for seller in sellers if UserRole.SELLER.value in (seller.roles or [])]
    seller_metrics = [
        AdminSellerEarningsRead(
            seller_id=seller.id,
            seller_name=seller.full_name,
            seller_email=seller.email,
            **_seller_earnings(db, seller.id).model_dump(),
        )
        for seller in sellers
    ]
    payouts_with_sellers = db.execute(
        select(SellerPayout, User).join(User, User.id == SellerPayout.seller_id)
        .order_by(SellerPayout.created_at.desc(), SellerPayout.id.desc())
        .limit(200)
    ).all()
    payout_rows = [
        AdminPayoutRead.model_validate({
            **{field: getattr(payout, field) for field in ("id", "seller_id", "amount", "status", "reference", "note", "created_at", "updated_at", "paid_at")},
            "seller_name": seller.full_name,
            "seller_email": seller.email,
        })
        for payout, seller in payouts_with_sellers
    ]
    return AdminPayoutDashboardRead(sellers=seller_metrics, payouts=payout_rows)


def create_payout(db: Session, details: PayoutCreate) -> SellerPayout:
    seller = db.scalar(
        select(User).where(User.id == details.seller_id).with_for_update()
    )
    if seller is not None and UserRole.SELLER.value not in (seller.roles or []):
        seller = None
    if seller is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Seller not found")
    balance = _seller_earnings(db, seller.id)
    if details.amount > balance.available_for_payout:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Payout exceeds the available balance of INR {balance.available_for_payout}.",
        )
    payout = SellerPayout(
        seller_id=seller.id,
        amount=details.amount.quantize(CENT),
        status=PayoutStatus.PENDING.value,
        reference=details.reference.strip() if details.reference else None,
        note=details.note.strip() if details.note else None,
    )
    db.add(payout)
    db.commit()
    db.refresh(payout)
    return payout


def update_payout(db: Session, payout_id: int, details: PayoutUpdate) -> SellerPayout:
    payout = db.scalar(select(SellerPayout).where(SellerPayout.id == payout_id).with_for_update())
    if payout is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payout not found")
    current = PayoutStatus(payout.status)
    if details.status != current and details.status not in NEXT_STATUSES[current]:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Payout cannot move from {current.value} to {details.status.value}.")
    if details.status == PayoutStatus.PAID and current != PayoutStatus.PAID:
        db.scalar(select(User.id).where(User.id == payout.seller_id).with_for_update())
        balance = _seller_earnings(db, payout.seller_id)
        paid = db.scalar(
            select(func.coalesce(func.sum(SellerPayout.amount), 0)).where(
                SellerPayout.seller_id == payout.seller_id,
                SellerPayout.status == PayoutStatus.PAID.value,
                SellerPayout.id != payout.id,
            ).with_for_update()
        )
        paid_total = paid or Decimal("0.00")
        # A locked seller row is also held when payouts are created; this final guard
        # protects against earnings being cancelled while a payout was processing.
        if payout.amount + paid_total > balance.eligible_earnings:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Paid seller earnings no longer cover this payout.")
    payout.status = details.status.value
    if "reference" in details.model_fields_set:
        payout.reference = details.reference.strip() if details.reference else None
    if "note" in details.model_fields_set:
        payout.note = details.note.strip() if details.note else None
    if details.status == PayoutStatus.PAID:
        if current != PayoutStatus.PAID:
            payout.paid_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(payout)
    return payout
