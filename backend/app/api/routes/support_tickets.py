from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.auth_deps import require_roles
from app.api.deps import get_db
from app.models.auth import User, UserRole
from app.schemas.support_tickets import (
    AdminSupportTicketDetailRead,
    AdminSupportTicketRead,
    SupportTicketCreate,
    SupportTicketDetailRead,
    SupportTicketRead,
    SupportTicketReplyCreate,
    SupportTicketStatusUpdate,
)
from app.services import support_tickets as ticket_service

buyer_router = APIRouter(prefix="/support/tickets", tags=["support tickets"])
admin_router = APIRouter(prefix="/admin/support/tickets", tags=["support tickets"])


@buyer_router.post("", response_model=SupportTicketRead, status_code=status.HTTP_201_CREATED)
def create_ticket(
    ticket_in: SupportTicketCreate,
    db: Session = Depends(get_db),
    buyer: User = Depends(require_roles(UserRole.BUYER)),
) -> SupportTicketRead:
    return ticket_service.create_ticket(db, buyer, ticket_in)


@buyer_router.get("", response_model=list[SupportTicketRead])
def list_my_tickets(
    db: Session = Depends(get_db),
    buyer: User = Depends(require_roles(UserRole.BUYER)),
) -> list[SupportTicketRead]:
    return ticket_service.list_buyer_tickets(db, buyer.id)


@buyer_router.get("/{ticket_id}", response_model=SupportTicketDetailRead)
def get_my_ticket(
    ticket_id: int,
    db: Session = Depends(get_db),
    buyer: User = Depends(require_roles(UserRole.BUYER)),
) -> SupportTicketDetailRead:
    return ticket_service.get_buyer_ticket(db, buyer.id, ticket_id)


@admin_router.get("", response_model=list[AdminSupportTicketRead])
def list_all_tickets(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN)),
) -> list[AdminSupportTicketRead]:
    return ticket_service.list_admin_tickets(db)


@admin_router.get("/{ticket_id}", response_model=AdminSupportTicketDetailRead)
def get_ticket(
    ticket_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN)),
) -> AdminSupportTicketDetailRead:
    return ticket_service.get_admin_ticket(db, ticket_id)


@admin_router.post("/{ticket_id}/replies", response_model=AdminSupportTicketDetailRead)
def reply_to_ticket(
    ticket_id: int,
    reply_in: SupportTicketReplyCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_roles(UserRole.ADMIN)),
) -> AdminSupportTicketDetailRead:
    return ticket_service.reply_to_ticket(db, ticket_id, admin, reply_in)


@admin_router.patch("/{ticket_id}/status", response_model=AdminSupportTicketDetailRead)
def update_ticket_status(
    ticket_id: int,
    update_in: SupportTicketStatusUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN)),
) -> AdminSupportTicketDetailRead:
    return ticket_service.update_ticket_status(db, ticket_id, update_in)
