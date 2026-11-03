from functools import lru_cache
from typing import Literal

from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "CampusKart API"
    api_v1_prefix: str = "/api/v1"
    database_url: str = "mysql+pymysql://root:change-me@localhost:3306/campuskart"
    frontend_origins: list[str] = ["http://localhost:5173"]
    frontend_base_url: str = "http://localhost:5173"
    jwt_secret_key: SecretStr
    access_token_minutes: int = 15
    refresh_session_days: int = 30
    refresh_cookie_secure: bool = True
    refresh_cookie_samesite: Literal["lax", "strict", "none"] = "lax"
    email_verification_token_minutes: int = 60
    password_reset_token_minutes: int = 30
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: SecretStr | None = None
    smtp_from_email: str | None = None
    smtp_from_name: str = "CampusKart"
    smtp_use_tls: bool = True
    smtp_use_ssl: bool = False
    smtp_timeout_seconds: int = 10
    media_root: str = "uploads"
    razorpay_key_id: str | None = None
    razorpay_key_secret: SecretStr | None = None
    razorpay_webhook_secret: SecretStr | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @model_validator(mode="after")
    def validate_auth_settings(self) -> "Settings":
        signing_key = self.jwt_secret_key.get_secret_value()
        if len(signing_key) < 32 or "replace-with" in signing_key.casefold():
            raise ValueError("JWT_SECRET_KEY must be a generated secret of at least 32 characters")
        if self.access_token_minutes < 1:
            raise ValueError("ACCESS_TOKEN_MINUTES must be at least 1")
        if self.refresh_session_days < 1:
            raise ValueError("REFRESH_SESSION_DAYS must be at least 1")
        if self.refresh_cookie_samesite == "none" and not self.refresh_cookie_secure:
            raise ValueError("REFRESH_COOKIE_SECURE must be true when REFRESH_COOKIE_SAMESITE is none")
        if self.email_verification_token_minutes < 1:
            raise ValueError("EMAIL_VERIFICATION_TOKEN_MINUTES must be at least 1")
        if self.password_reset_token_minutes < 1:
            raise ValueError("PASSWORD_RESET_TOKEN_MINUTES must be at least 1")
        if self.smtp_port < 1 or self.smtp_port > 65535:
            raise ValueError("SMTP_PORT must be between 1 and 65535")
        if self.smtp_timeout_seconds < 1:
            raise ValueError("SMTP_TIMEOUT_SECONDS must be at least 1")
        if self.smtp_use_tls and self.smtp_use_ssl:
            raise ValueError("Set only one of SMTP_USE_TLS or SMTP_USE_SSL")
        if bool(self.razorpay_key_id) != bool(self.razorpay_key_secret):
            raise ValueError("Configure both RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET")
        if self.razorpay_key_id and not self.razorpay_key_id.startswith("rzp_test_"):
            raise ValueError("CampusKart currently accepts Razorpay test-mode keys only (rzp_test_...)")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
