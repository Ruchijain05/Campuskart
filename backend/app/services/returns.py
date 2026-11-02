from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.auth import User
from app.models.order import Order
from app.models.return_request import ReturnRequest
from app.schemas.returns import (
    AdminReturnRequestRead,
    RefundStatus,
    ReturnDecisionUpdate,
    ReturnRequestCreate,
    ReturnRequestRead,
    ReturnStatus,
)
from app.services.notifications import create_notification
from app.services.email_notifications import send_email


def _buyer_read(request: ReturnRequest, order: Order) -> ReturnRequestRead:
    return ReturnRequestRead(
        id=request.id,
        order_id=order.id,
        request_type=request.request_type,
        reason=request.reason,
        status=request.status,
        refund_status=request.refund_status,
        review_note=request.review_note,
        order_status=order.status,
        order_total=order.total,
        payment_method=order.payment_method,
        created_at=request.created_at,
        reviewed_at=request.reviewed_at,
        refund_updated_at=request.refund_updated_at,
    )


def _admin_read(request: ReturnRequest, order: Order, buyer: User) -> AdminReturnRequestRead:
    return AdminReturnRequestRead(
        **_buyer_read(request, order).model_dump(),
        buyer_id=buyer.id,
        buyer_name=buyer.full_name,
        buyer_email=buyer.email,
    )


def create_return_request(
    db: Session,
    *,
    order_id: int,
    buyer_id: int,
    details: ReturnRequestCreate,
) -> ReturnRequestRead:
    order = db.scalar(select(Order).where(Order.id == order_id, Order.user_id == buyer_id).with_for_update())
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    if order.status != "delivered":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Returns and refunds are available only for delivered orders")
    existing = db.scalar(select(ReturnRequest.id).where(ReturnRequest.order_id == order_id))
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A return or refund request already exists for this order")
    request = ReturnRequest(
        order_id=order.id,
        buyer_id=buyer_id,
        request_type=details.request_type.value,
        reason=details.reason,
    )
    db.add(request)
    try:
        db.commit()
        db.refresh(request)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A request already exists for this order") from exc
    return _buyer_read(request, order)


def list_buyer_requests(db: Session, buyer_id: int) -> list[ReturnRequestRead]:
    rows = db.execute(
        select(ReturnRequest, Order)
        .join(Order, Order.id == ReturnRequest.order_id)
        .where(ReturnRequest.buyer_id == buyer_id)
        .order_by(ReturnRequest.created_at.desc(), ReturnRequest.id.desc())
    ).all()
    return [_buyer_read(request, order) for request, order in rows]


def list_admin_requests(db: Session) -> list[AdminReturnRequestRead]:
    rows = db.execute(
        select(ReturnRequest, Order, User)
        .join(Order, Order.id == ReturnRequest.order_id)
        .join(User, User.id == ReturnRequest.buyer_id)
        .order_by(ReturnRequest.created_at.desc(), ReturnRequest.id.desc())
    ).all()
    return [_admin_read(request, order, buyer) for request, order, buyer in rows]


def review_request(
    db: Session,
    *,
    request_id: int,
    decision: ReturnDecisionUpdate,
) -> AdminReturnRequestRead:
    row = db.execute(
        select(ReturnRequest, Order, User)
        .join(Order, Order.id == ReturnRequest.order_id)
        .join(User, User.id == ReturnRequest.buyer_id)
        .where(ReturnRequest.id == request_id)
        .with_for_update()
    ).first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Return request not found")
    request, order, buyer = row
    if request.status != ReturnStatus.PENDING.value:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This request has already been reviewed")
    request.status = decision.decision.value
    request.refund_status = RefundStatus.PENDING.value if decision.decision == ReturnStatus.APPROVED else RefundStatus.NOT_APPLICABLE.value
    request.review_note = decision.review_note
    request.reviewed_at = datetime.now(timezone.utc)
    decision_text = "approved" if decision.decision == ReturnStatus.APPROVED else "rejected"
    create_notification(
        db,
        user_id=buyer.id,
        kind="return_decision",
        title=f"Your {request.request_type} request was {decision_text}",
        message=f"Your request for order #{order.id} was {decision_text}." + (f" Admin note: {decision.review_note}" if decision.review_note else ""),
        link="/returns",
    )
    buyer_email = buyer.email
    buyer_name = buyer.full_name
    order_id = order.id
    request_type = request.request_type
    refund_status = request.refund_status
    review_note = decision.review_note
    db.commit()
    db.refresh(request)
    send_email(
        buyer_email,
        f"CampusKart {request_type} request {decision_text}",
        f"Hi {buyer_name},\n\nYour {request_type} request for order #{order_id} was {decision_text}.\n{('Admin note: ' + review_note + chr(10)) if review_note else ''}\nCurrent refund status: {refund_status.replace('_', ' ')}.\n\nSign in to CampusKart to view the latest details.",
    )
    return _admin_read(request, order, buyer)


REFUND_TRANSITIONS = {
    RefundStatus.PENDING: {RefundStatus.PROCESSING, RefundStatus.REFUNDED, RefundStatus.FAILED},
    RefundStatus.PROCESSING: {RefundStatus.REFUNDED, RefundStatus.FAILED},
    RefundStatus.FAILED: {RefundStatus.PROCESSING},
    RefundStatus.REFUNDED: set(),
    RefundStatus.NOT_APPLICABLE: set(),
}


def update_refund_status(db: Session, *, request_id: int, next_status: RefundStatus) -> AdminReturnRequestRead:
    row = db.execute(
        select(ReturnRequest, Order, User)
        .join(Order, Order.id == ReturnRequest.order_id)
        .join(User, User.id == ReturnRequest.buyer_id)
        .where(ReturnRequest.id == request_id)
        .with_for_update()
    ).first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Return request not found")
    request, order, buyer = row
    if request.status != ReturnStatus.APPROVED.value:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Refund status can be changed only for approved requests")
    current = RefundStatus(request.refund_status)
    if next_status != current and next_status not in REFUND_TRANSITIONS[current]:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Refund cannot move from {current.value} to {next_status.value}")
    if next_status != current:
        request.refund_status = next_status.value
        request.refund_updated_at = datetime.now(timezone.utc)
        create_notification(
            db,
            user_id=buyer.id,
            kind="refund_status",
            title="Refund status updated",
            message=f"Your refund for order #{order.id} is now {next_status.value}.",
            link="/returns",
        )
        buyer_email = buyer.email
        buyer_name = buyer.full_name
        order_id = order.id
        db.commit()
        db.refresh(request)
        send_email(
            buyer_email,
            f"CampusKart refund update for order #{order_id}",
            f"Hi {buyer_name},\n\nThe refund status for your order #{order_id} is now {next_status.value.replace('_', ' ')}.\n\nSign in to CampusKart to view the latest details.",
        )
    return _admin_read(request, order, buyer)
