from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models.auth import (
    SellerApplication,
    SellerApplicationStatus,
    User,
    UserRole,
)
from app.schemas.auth import SellerApplicationCreate
from app.services.email_notifications import send_email
from app.services.notifications import create_notification


def create_seller_application(
    db: Session,
    user: User,
    application_in: SellerApplicationCreate,
) -> SellerApplication:
    existing = db.scalar(
        select(SellerApplication).where(SellerApplication.user_id == user.id)
    )
    if existing is not None:
        if existing.status == SellerApplicationStatus.PENDING:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A seller application is already pending",
            )
        if existing.status == SellerApplicationStatus.APPROVED:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Seller access has already been approved",
            )
        existing.message = application_in.message
        existing.status = SellerApplicationStatus.PENDING
        existing.reviewed_by = None
        existing.review_note = None
        existing.reviewed_at = None
        db.commit()
        db.refresh(existing)
        return existing

    application = SellerApplication(user_id=user.id, message=application_in.message)
    db.add(application)
    db.commit()
    db.refresh(application)
    return application


def list_seller_applications(db: Session) -> list[SellerApplication]:
    return list(
        db.scalars(
            select(SellerApplication)
            .where(SellerApplication.status == SellerApplicationStatus.PENDING)
            .order_by(SellerApplication.created_at.asc())
        ).all()
    )


def review_seller_application(
    db: Session,
    *,
    application_id: int,
    admin: User,
    decision: str,
    review_note: str | None,
) -> SellerApplication:
    application = db.get(SellerApplication, application_id)
    if application is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
    if application.status != SellerApplicationStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Application has already been reviewed",
        )

    reviewed_status = SellerApplicationStatus(decision)
    applicant = db.get(User, application.user_id)
    if applicant is None:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Applicant account no longer exists",
        )
    if reviewed_status == SellerApplicationStatus.APPROVED and UserRole.SELLER.value in (applicant.roles or []):
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only buyer accounts can be approved for seller access.",
        )
    reviewed_at = datetime.now(timezone.utc)
    result = db.execute(
        update(SellerApplication)
        .where(
            SellerApplication.id == application_id,
            SellerApplication.status == SellerApplicationStatus.PENDING,
        )
        .values(
            status=reviewed_status,
            reviewed_by=admin.id,
            review_note=review_note,
            reviewed_at=reviewed_at,
        )
    )
    if result.rowcount != 1:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Application has already been reviewed",
        )
    if reviewed_status == SellerApplicationStatus.APPROVED:
        applicant.roles = list(dict.fromkeys([*(applicant.roles or [UserRole.BUYER.value]), UserRole.SELLER.value]))
        applicant.role = UserRole.SELLER

    create_notification(
        db,
        user_id=application.user_id,
        kind="account",
        title="Seller application reviewed",
        message=(
            "Your seller application was approved. You can now list products."
            if reviewed_status == SellerApplicationStatus.APPROVED
            else "Your seller application was not approved. You can review the decision in your account."
        ),
        link="/account",
    )

    applicant_email = applicant.email
    applicant_name = applicant.full_name
    db.commit()
    db.refresh(application)
    outcome = "approved" if reviewed_status == SellerApplicationStatus.APPROVED else "rejected"
    note = f"\nAdmin note: {review_note}" if review_note else ""
    send_email(
        applicant_email,
        f"CampusKart seller application {outcome}",
        f"Hi {applicant_name},\n\nYour seller application was {outcome}.{note}\n\nSign in to CampusKart to view your account.",
    )
    return application
