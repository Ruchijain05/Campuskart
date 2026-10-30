import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from pwdlib import PasswordHash

from app.core.config import settings

password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    return password_hash.verify(password, hashed_password)


def hash_token_id(token_id: str) -> str:
    return hashlib.sha256(token_id.encode("utf-8")).hexdigest()


def create_access_token(user_id: int, family_id: str) -> tuple[str, str, datetime]:
    now = datetime.now(timezone.utc)
    token_id = secrets.token_urlsafe(32)
    expires_at = now + timedelta(minutes=settings.access_token_minutes)
    token = jwt.encode(
        {
            "sub": str(user_id),
            "family": family_id,
            "jti": token_id,
            "type": "access",
            "iat": now,
            "exp": expires_at,
            "iss": "campuskart",
            "aud": "campuskart-web",
        },
        settings.jwt_secret_key.get_secret_value(),
        algorithm="HS256",
    )
    return token, hash_token_id(token_id), expires_at


def decode_token(token: str, *, token_type: str) -> dict[str, object]:
    payload = jwt.decode(
        token,
        settings.jwt_secret_key.get_secret_value(),
        algorithms=["HS256"],
        audience="campuskart-web",
        issuer="campuskart",
        options={"require": ["exp", "iat", "sub", "type"]},
    )
    if payload.get("type") != token_type:
        raise jwt.InvalidTokenError("Unexpected token type")
    return payload
