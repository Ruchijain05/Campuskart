import jwt
from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.auth_deps import get_current_user, oauth2_scheme, require_roles
from app.api.deps import get_db
from app.core.security import decode_token
from app.models.auth import User, UserRole
from app.schemas.auth import (
    OAuth2Token,
    SellerApplicationCreate,
    SellerApplicationRead,
    SellerApplicationReview,
    UserRead,
    UserRegister,
)
from app.services import auth as auth_service
from app.services.notifications import create_notification

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post(
    "/token",
    response_model=OAuth2Token,
    summary="Sign in with email and password",
)
def issue_access_token(
    credentials: OAuth2PasswordRequestForm = Depends(),
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
    return OAuth2Token(access_token=auth_service.create_access_session(db, user.id))


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(
    user_in: UserRegister,
    db: Session = Depends(get_db),
) -> UserRead:
    if auth_service.get_user_by_email(db, str(user_in.email)) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email is already registered")
    try:
        user = auth_service.register_user(db, user_in)
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


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    token: str = Depends(oauth2_scheme),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    try:
        payload = decode_token(token, token_type="access")
        family_id = str(payload["family"])
        token_id = str(payload["jti"])
    except (jwt.InvalidTokenError, KeyError, TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    auth_service.revoke_access_session(
        db,
        user_id=user.id,
        family_id=family_id,
        token_id=token_id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


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
