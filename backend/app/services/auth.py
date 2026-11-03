from datetime import datetime, timedelta, timezone
import secrets
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import (
    create_access_token,
    hash_password,
    hash_token_id,
    verify_password,
)
from app.models.auth import (
    AuthSession,
    EmailActionToken,
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
        is_email_verified=False,
    )
    db.add(user)
    db.flush()
    return user


def create_email_action_token(db: Session, user: User, purpose: str) -> str:
    now = datetime.now(timezone.utc)
    lifetime = (
        timedelta(minutes=settings.email_verification_token_minutes)
        if purpose == "verify_email"
        else timedelta(minutes=settings.password_reset_token_minutes)
    )
    db.execute(
        update(EmailActionToken)
        .where(
            EmailActionToken.user_id == user.id,
            EmailActionToken.purpose == purpose,
            EmailActionToken.used_at.is_(None),
        )
        .values(used_at=now)
    )
    token = secrets.token_urlsafe(48)
    db.add(
        EmailActionToken(
            user_id=user.id,
            token_hash=hash_token_id(token),
            purpose=purpose,
            expires_at=now + lifetime,
        )
    )
    db.flush()
    return token


def send_email_action_link(user: User, token: str, purpose: str) -> bool:
    base_url = settings.frontend_base_url.rstrip("/")
    if purpose == "verify_email":
        link = f"{base_url}/verify-email?token={token}"
        subject = "Verify your CampusKart email"
        body = (
            f"Hi {user.full_name},\n\n"
            f"Verify your email address by opening this link:\n{link}\n\n"
            f"This link expires in {settings.email_verification_token_minutes} minutes. "
            "If you did not create a CampusKart account, you can ignore this email."
        )
    else:
        link = f"{base_url}/reset-password?token={token}"
        subject = "Reset your CampusKart password"
        body = (
            f"Hi {user.full_name},\n\n"
            f"Reset your CampusKart password by opening this link:\n{link}\n\n"
            f"This link expires in {settings.password_reset_token_minutes} minutes. "
            "If you did not request a password reset, you can ignore this email."
        )
    return send_email(user.email, subject, body)


def consume_email_action_token(
    db: Session,
    *,
    token: str,
    purpose: str,
) -> User | None:
    now = datetime.now(timezone.utc)
    action_token = db.scalar(
        select(EmailActionToken).where(
            EmailActionToken.token_hash == hash_token_id(token),
            EmailActionToken.purpose == purpose,
            EmailActionToken.used_at.is_(None),
            EmailActionToken.expires_at > now,
        )
    )
    if action_token is None:
        return None
    consumed = db.execute(
        update(EmailActionToken)
        .where(
            EmailActionToken.id == action_token.id,
            EmailActionToken.used_at.is_(None),
            EmailActionToken.expires_at > now,
        )
        .values(used_at=now)
        .execution_options(synchronize_session=False)
    )
    if consumed.rowcount != 1:
        db.rollback()
        return None
    user = db.get(User, action_token.user_id)
    if user is None:
        db.rollback()
        return None
    return user


def verify_user_email(db: Session, token: str) -> bool:
    user = consume_email_action_token(db, token=token, purpose="verify_email")
    if user is None:
        return False
    user.is_email_verified = True
    db.commit()
    return True


def reset_user_password(db: Session, token: str, password: str) -> bool:
    user = consume_email_action_token(db, token=token, purpose="password_reset")
    if user is None:
        return False
    user.password_hash = hash_password(password)
    now = datetime.now(timezone.utc)
    db.execute(
        update(EmailActionToken)
        .where(
            EmailActionToken.user_id == user.id,
            EmailActionToken.purpose == "password_reset",
            EmailActionToken.used_at.is_(None),
        )
        .values(used_at=now)
    )
    db.execute(
        update(AuthSession)
        .where(
            AuthSession.user_id == user.id,
            AuthSession.revoked_at.is_(None),
        )
        .values(revoked_at=now)
    )
    db.commit()
    return True


def authenticate_user(db: Session, email: str, password: str) -> User | None:
    user = get_user_by_email(db, email)
    if user is None:
        hash_password(password)
        return None
    if not verify_password(password, user.password_hash) or not user.is_active:
        return None
    return user


def create_access_session(db: Session, user_id: int) -> tuple[str, str, datetime]:
    family_id = str(uuid4())
    access_token, token_hash, _ = create_access_token(user_id, family_id)
    refresh_token = secrets.token_urlsafe(48)
    session_expires_at = datetime.now(timezone.utc) + timedelta(days=settings.refresh_session_days)
    db.add(
        AuthSession(
            user_id=user_id,
            family_id=family_id,
            token_hash=token_hash,
            refresh_token_hash=hash_token_id(refresh_token),
            expires_at=session_expires_at,
        )
    )
    db.commit()
    return access_token, refresh_token, session_expires_at


def create_refreshed_access_token(db: Session, refresh_token: str) -> str | None:
    session = db.scalar(
        select(AuthSession).where(
            AuthSession.refresh_token_hash == hash_token_id(refresh_token),
            AuthSession.revoked_at.is_(None),
            AuthSession.expires_at > datetime.now(timezone.utc),
        )
    )
    if session is None:
        return None
    user = db.get(User, session.user_id)
    if user is None or not user.is_active:
        return None
    access_token, _, _ = create_access_token(user.id, session.family_id)
    return access_token


def revoke_access_family(
    db: Session,
    *,
    user_id: int,
    family_id: str,
) -> None:
    db.execute(
        update(AuthSession)
        .where(
            AuthSession.user_id == user_id,
            AuthSession.family_id == family_id,
            AuthSession.revoked_at.is_(None),
        )
        .values(revoked_at=datetime.now(timezone.utc))
    )
    db.commit()


def revoke_refresh_session(db: Session, refresh_token: str) -> bool:
    session = db.scalar(
        select(AuthSession).where(
            AuthSession.refresh_token_hash == hash_token_id(refresh_token),
            AuthSession.revoked_at.is_(None),
        )
    )
    if session is None:
        return False
    revoke_access_family(db, user_id=session.user_id, family_id=session.family_id)
    return True


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
