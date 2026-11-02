from datetime import datetime, timezone
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.security import (
    create_access_token,
    hash_password,
    hash_token_id,
    verify_password,
)
from app.models.auth import (
    AuthSession,
    SellerApplication,
    SellerApplicationStatus,
    User,
    UserRole,
)
from app.schemas.auth import SellerApplicationCreate, UserRegister
from app.services.notifications import create_notification
from app.services.email_notifications import send_email


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == email))


def register_user(db: Session, user_in: UserRegister) -> User:
    user = User(
        full_name=user_in.full_name,
        email=str(user_in.email).casefold(),
        phone_number=user_in.phone_number,
        password_hash=hash_password(user_in.password),
        role=UserRole.BUYER,
    )
    db.add(user)
    db.flush()
    return user


def authenticate_user(db: Session, email: str, password: str) -> User | None:
    user = get_user_by_email(db, email)
    if user is None:
        hash_password(password)
        return None
    if not verify_password(password, user.password_hash) or not user.is_active:
        return None
    return user


def create_access_session(db: Session, user_id: int) -> str:
    family_id = str(uuid4())
    access_token, token_hash, expires_at = create_access_token(user_id, family_id)
    db.add(
        AuthSession(
            user_id=user_id,
            family_id=family_id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
    )
    db.commit()
    return access_token


def revoke_access_session(
    db: Session,
    *,
    user_id: int,
    family_id: str,
    token_id: str,
) -> None:
    db.execute(
        update(AuthSession)
        .where(
            AuthSession.user_id == user_id,
            AuthSession.family_id == family_id,
            AuthSession.token_hash == hash_token_id(token_id),
            AuthSession.revoked_at.is_(None),
        )
        .values(revoked_at=datetime.now(timezone.utc))
    )
    db.commit()


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
