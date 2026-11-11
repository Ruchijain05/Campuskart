from collections.abc import Callable
from functools import lru_cache
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.config import settings
from app.models.auth import User, UserRole

bearer_scheme = HTTPBearer(auto_error=False)
@lru_cache(maxsize=1)
def _jwks_client() -> jwt.PyJWKClient:
    if not settings.supabase_url:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="SUPABASE_URL is not configured on the API.",
        )
    return jwt.PyJWKClient(
        f"{settings.supabase_url}/auth/v1/.well-known/jwks.json",
        cache_jwk_set=True,
    )


def _decode_supabase_token(token: str) -> dict[str, object]:
    try:
        signing_key = _jwks_client().get_signing_key_from_jwt(token)
        if signing_key.algorithm_name not in {"ES256", "RS256"}:
            raise jwt.InvalidTokenError("Unsupported Supabase signing algorithm")
        return jwt.decode(
            token,
            signing_key.key,
            algorithms=[signing_key.algorithm_name],
            audience=settings.supabase_jwt_audience,
            issuer=f"{settings.supabase_url}/auth/v1",
            options={"require": ["exp", "iat", "sub", "aud", "iss"]},
        )
    except jwt.PyJWKClientConnectionError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Supabase token verification is temporarily unavailable.",
        ) from exc
    except (jwt.PyJWTError, TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired Supabase access token.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


def _claim_string(claims: dict[str, object], key: str) -> str | None:
    value = claims.get(key)
    return value.strip() if isinstance(value, str) and value.strip() else None


def _new_user_from_claims(claims: dict[str, object], auth_user_id: UUID) -> User:
    email = _claim_string(claims, "email")
    if email is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Supabase account must have an email address.",
        )

    metadata = claims.get("user_metadata")
    user_metadata = metadata if isinstance(metadata, dict) else {}
    full_name = (
        user_metadata.get("full_name")
        or user_metadata.get("name")
        or email.partition("@")[0]
    )
    phone_number = user_metadata.get("phone_number", "")
    return User(
        auth_user_id=auth_user_id,
        full_name=str(full_name).strip()[:120] or email.partition("@")[0],
        email=email.casefold(),
        phone_number=str(phone_number)[:16] if isinstance(phone_number, str) else "",
        role=UserRole.BUYER,
        is_active=True,
        is_email_verified=True,
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None or credentials.scheme.casefold() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="A Supabase bearer token is required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    claims = _decode_supabase_token(credentials.credentials)
    try:
        auth_user_id = UUID(str(claims["sub"]))
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Supabase access token has an invalid subject.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    user = db.scalar(select(User).where(User.auth_user_id == auth_user_id))
    if user is None:
        candidate = _new_user_from_claims(claims, auth_user_id)
        email_owner = db.scalar(select(User.id).where(User.email == candidate.email))
        if email_owner is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This email is already linked to a CampusKart account.",
            )
        db.add(candidate)
        try:
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            user = db.scalar(select(User).where(User.auth_user_id == auth_user_id))
            if user is None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="A CampusKart account already exists for this email.",
                ) from exc
        else:
            db.refresh(candidate)
            user = candidate

    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is unavailable.",
        )
    return user


def require_roles(*roles: UserRole) -> Callable[..., User]:
    def role_dependency(user: User = Depends(get_current_user)) -> User:
        assigned = user.roles or [user.role.value]
        if user.role.value not in assigned or user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return user

    return role_dependency
