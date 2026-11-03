from datetime import datetime, timezone

import jwt
from fastapi import APIRouter, Cookie, Depends, Header, HTTPException, Response, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.auth_deps import get_current_user, require_roles
from app.api.deps import get_db
from app.core.config import settings
from app.core.security import decode_token
from app.models.auth import User, UserRole
from app.schemas.auth import (
    EmailAddressInput,
    EmailTokenInput,
    OAuth2Token,
    PasswordResetInput,
    SellerApplicationCreate,
    SellerApplicationRead,
    SellerApplicationReview,
    UserRead,
    UserRegister,
)
from app.services import auth as auth_service
from app.services.notifications import create_notification

router = APIRouter(prefix="/auth", tags=["authentication"])
refresh_cookie_name = "campuskart_refresh"
refresh_cookie_path = f"{settings.api_v1_prefix}/auth"
optional_oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.api_v1_prefix}/auth/token",
    auto_error=False,
)


def _set_refresh_cookie(response: Response, token: str, expires_at: datetime) -> None:
    max_age = max(0, int((expires_at - datetime.now(timezone.utc)).total_seconds()))
    response.set_cookie(
        key=refresh_cookie_name,
        value=token,
        max_age=max_age,
        expires=expires_at,
        path=refresh_cookie_path,
        secure=settings.refresh_cookie_secure,
        httponly=True,
        samesite=settings.refresh_cookie_samesite,
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(
        key=refresh_cookie_name,
        path=refresh_cookie_path,
        secure=settings.refresh_cookie_secure,
        httponly=True,
        samesite=settings.refresh_cookie_samesite,
    )


def _require_allowed_origin(origin: str | None) -> None:
    if origin not in settings.frontend_origins:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid request origin")


@router.post(
    "/token",
    response_model=OAuth2Token,
    summary="Sign in with email and password",
)
def issue_access_token(
    response: Response,
    credentials: OAuth2PasswordRequestForm = Depends(),
    origin: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> OAuth2Token:
    user = auth_service.authenticate_user(
        db,
        credentials.username.strip().casefold(),
        credentials.password,
    )
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_email_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Please verify your email address before signing in.",
        )
    access_token, refresh_token, expires_at = auth_service.create_access_session(db, user.id)
    if origin in settings.frontend_origins:
        _set_refresh_cookie(response, refresh_token, expires_at)
    return OAuth2Token(access_token=access_token)


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(
    user_in: UserRegister,
    db: Session = Depends(get_db),
) -> UserRead:
    if auth_service.get_user_by_email(db, str(user_in.email)) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email is already registered")
    try:
        user = auth_service.register_user(db, user_in)
        verification_token = auth_service.create_email_action_token(db, user, "verify_email")
        if not auth_service.send_email_action_link(user, verification_token, "verify_email"):
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="We could not send the verification email. Please try again later.",
            )
        if user.role == UserRole.BUYER:
            create_notification(
                db,
                user_id=user.id,
                kind="account",
                title="Welcome to CampusKart",
                message="Your account is ready. We’ll keep you updated about important account activity and orders.",
                link="/account",
            )
        db.commit()
        db.refresh(user)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email is already registered",
        ) from exc
    return user


@router.post("/forgot-password", status_code=status.HTTP_202_ACCEPTED)
def request_password_reset(
    email_in: EmailAddressInput,
    db: Session = Depends(get_db),
) -> dict[str, str]:
    user = auth_service.get_user_by_email(db, str(email_in.email))
    if user is not None and user.is_active:
        token = auth_service.create_email_action_token(db, user, "password_reset")
        db.commit()
        auth_service.send_email_action_link(user, token, "password_reset")
    return {"message": "If an account exists for that email, password reset instructions will be sent."}


@router.post("/reset-password")
def reset_password(
    reset_in: PasswordResetInput,
    db: Session = Depends(get_db),
) -> dict[str, str]:
    if not auth_service.reset_user_password(db, reset_in.token, reset_in.password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This password reset link is invalid or has expired. Request a new one.",
        )
    return {"message": "Password reset successfully. You can now sign in."}


@router.post("/verify-email")
def verify_email(
    verification_in: EmailTokenInput,
    db: Session = Depends(get_db),
) -> dict[str, str]:
    if not auth_service.verify_user_email(db, verification_in.token):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This verification link is invalid or has expired. Request a new one.",
        )
    return {"message": "Email verified successfully. You can now sign in."}


@router.post("/resend-verification", status_code=status.HTTP_202_ACCEPTED)
def resend_verification(
    email_in: EmailAddressInput,
    db: Session = Depends(get_db),
) -> dict[str, str]:
    user = auth_service.get_user_by_email(db, str(email_in.email))
    if user is not None and user.is_active and not user.is_email_verified:
        token = auth_service.create_email_action_token(db, user, "verify_email")
        db.commit()
        auth_service.send_email_action_link(user, token, "verify_email")
    return {"message": "If the account needs verification, a new link will be sent."}


@router.post("/refresh", response_model=OAuth2Token)
def refresh_access_token(
    refresh_token: str | None = Cookie(default=None, alias=refresh_cookie_name),
    origin: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> OAuth2Token:
    _require_allowed_origin(origin)
    if not refresh_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session has expired")
    refreshed = auth_service.create_refreshed_access_token(db, refresh_token)
    if refreshed is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session has expired")
    return OAuth2Token(access_token=refreshed)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    response: Response,
    token: str | None = Depends(optional_oauth2_scheme),
    refresh_token: str | None = Cookie(default=None, alias=refresh_cookie_name),
    origin: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> Response:
    if refresh_token:
        _require_allowed_origin(origin)
        if auth_service.revoke_refresh_session(db, refresh_token):
            _clear_refresh_cookie(response)
            response.status_code = status.HTTP_204_NO_CONTENT
            return response
    if not token:
        _clear_refresh_cookie(response)
        response.status_code = status.HTTP_204_NO_CONTENT
        return response
    try:
        payload = decode_token(token, token_type="access")
        user_id = int(str(payload["sub"]))
        family_id = str(payload["family"])
    except (jwt.InvalidTokenError, KeyError, TypeError, ValueError) as exc:
        _clear_refresh_cookie(response)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    auth_service.revoke_access_family(
        db,
        user_id=user_id,
        family_id=family_id,
    )
    _clear_refresh_cookie(response)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.get("/me", response_model=UserRead)
def get_me(user: User = Depends(get_current_user)) -> UserRead:
    return user


@router.post(
    "/seller-applications",
    response_model=SellerApplicationRead,
    status_code=status.HTTP_201_CREATED,
)
def apply_to_become_seller(
    application_in: SellerApplicationCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.BUYER)),
) -> SellerApplicationRead:
    try:
        return auth_service.create_seller_application(db, user, application_in)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A seller application already exists",
        ) from exc


@router.get(
    "/seller-applications",
    response_model=list[SellerApplicationRead],
)
def list_seller_applications(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN)),
) -> list[SellerApplicationRead]:
    return auth_service.list_seller_applications(db)


@router.patch(
    "/seller-applications/{application_id}",
    response_model=SellerApplicationRead,
)
def review_seller_application(
    application_id: int,
    review: SellerApplicationReview,
    db: Session = Depends(get_db),
    admin: User = Depends(require_roles(UserRole.ADMIN)),
) -> SellerApplicationRead:
    return auth_service.review_seller_application(
        db,
        application_id=application_id,
        admin=admin,
        decision=review.decision.value,
        review_note=review.review_note,
    )
