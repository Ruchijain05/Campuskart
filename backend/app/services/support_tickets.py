from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models.auth import User
from app.models.support_ticket import SupportTicket, SupportTicketMessage
from app.schemas.support_tickets import SupportTicketCreate, SupportTicketReplyCreate, SupportTicketStatusUpdate
from app.services.notifications import create_notification


def create_ticket(db: Session, buyer: User, ticket_in: SupportTicketCreate) -> SupportTicket:
    ticket = SupportTicket(
        buyer_id=buyer.id,
        subject=ticket_in.subject,
        category=ticket_in.category.value,
        description=ticket_in.description,
        status="open",
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    return ticket


def list_buyer_tickets(db: Session, buyer_id: int) -> list[SupportTicket]:
    return list(db.scalars(
        select(SupportTicket).where(SupportTicket.buyer_id == buyer_id)
        .order_by(SupportTicket.updated_at.desc(), SupportTicket.id.desc())
    ).all())


def get_buyer_ticket(db: Session, buyer_id: int, ticket_id: int) -> SupportTicket:
    ticket = db.scalar(
        select(SupportTicket)
        .options(selectinload(SupportTicket.messages))
        .where(SupportTicket.id == ticket_id, SupportTicket.buyer_id == buyer_id)
    )
    if ticket is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Support ticket not found")
    return ticket


def list_admin_tickets(db: Session) -> list[SupportTicket]:
    return list(db.scalars(
        select(SupportTicket).options(joinedload(SupportTicket.buyer))
        .order_by(SupportTicket.updated_at.desc(), SupportTicket.id.desc())
    ).unique().all())


def get_admin_ticket(db: Session, ticket_id: int) -> SupportTicket:
    ticket = db.scalar(
        select(SupportTicket)
        .options(joinedload(SupportTicket.buyer), selectinload(SupportTicket.messages))
        .where(SupportTicket.id == ticket_id)
    )
    if ticket is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Support ticket not found")
    return ticket


def reply_to_ticket(db: Session, ticket_id: int, admin: User, reply_in: SupportTicketReplyCreate) -> SupportTicket:
    ticket = db.scalar(select(SupportTicket).where(SupportTicket.id == ticket_id).with_for_update())
    if ticket is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Support ticket not found")
    db.add(SupportTicketMessage(
        ticket_id=ticket.id,
        sender_id=admin.id,
        sender_role="admin",
        sender_name=admin.full_name,
        body=reply_in.body,
    ))
    ticket.updated_at = datetime.now(timezone.utc)
    create_notification(
        db,
        user_id=ticket.buyer_id,
        kind="support_ticket",
        title="Support replied to your ticket",
        message=f"An admin replied to ticket #{ticket.id}: {ticket.subject}",
        link="/support",
    )
    db.commit()
    return get_admin_ticket(db, ticket_id)


def update_ticket_status(
    db: Session,
    ticket_id: int,
    update_in: SupportTicketStatusUpdate,
) -> SupportTicket:
    ticket = db.scalar(select(SupportTicket).where(SupportTicket.id == ticket_id).with_for_update())
    if ticket is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Support ticket not found")
    next_status = update_in.status.value
    if ticket.status != next_status:
        ticket.status = next_status
        create_notification(
            db,
            user_id=ticket.buyer_id,
            kind="support_ticket",
            title="Support ticket status updated",
            message=f"Ticket #{ticket.id} ({ticket.subject}) is now {next_status.replace('_', ' ')}.",
            link="/support",
        )
        db.commit()
    return get_admin_ticket(db, ticket_id)
