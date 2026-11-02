from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.auth_deps import require_roles
from app.api.deps import get_db
from app.models.auth import User, UserRole
from app.schemas.returns import AdminReturnRequestRead, RefundStatusUpdate, ReturnDecisionUpdate, ReturnRequestCreate, ReturnRequestRead
from app.services import returns as return_service

router = APIRouter(tags=["returns and refunds"])


@router.post("/orders/{order_id}/returns", response_model=ReturnRequestRead, status_code=status.HTTP_201_CREATED)
def request_return(
    order_id: int,
    details: ReturnRequestCreate,
    db: Session = Depends(get_db),
    buyer: User = Depends(require_roles(UserRole.BUYER)),
) -> ReturnRequestRead:
    return return_service.create_return_request(db, order_id=order_id, buyer_id=buyer.id, details=details)


@router.get("/returns", response_model=list[ReturnRequestRead])
def list_my_returns(
    db: Session = Depends(get_db),
    buyer: User = Depends(require_roles(UserRole.BUYER)),
) -> list[ReturnRequestRead]:
    return return_service.list_buyer_requests(db, buyer.id)


@router.get("/admin/returns", response_model=list[AdminReturnRequestRead])
def list_all_returns(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN)),
) -> list[AdminReturnRequestRead]:
    return return_service.list_admin_requests(db)


@router.patch("/admin/returns/{request_id}/decision", response_model=AdminReturnRequestRead)
def decide_return(
    request_id: int,
    decision: ReturnDecisionUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN)),
) -> AdminReturnRequestRead:
    return return_service.review_request(db, request_id=request_id, decision=decision)


@router.patch("/admin/returns/{request_id}/refund", response_model=AdminReturnRequestRead)
def change_refund_status(
    request_id: int,
    update_in: RefundStatusUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN)),
) -> AdminReturnRequestRead:
    return return_service.update_refund_status(db, request_id=request_id, next_status=update_in.status)
