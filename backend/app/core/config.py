from functools import lru_cache
from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "CampusKart API"
    api_v1_prefix: str = "/api/v1"
    mysql_source_url: SecretStr | None = None
    supabase_url: str | None = None
    supabase_jwt_audience: str = "authenticated"
    supabase_secret_key: SecretStr | None = None
    supabase_service_role_key: SecretStr | None = None
    database_url: str
    frontend_origins: list[str] = ["http://localhost:5173"]
    frontend_base_url: str = "http://localhost:5173"
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
        env_ignore_empty=True,
        extra="ignore",
    )

    @model_validator(mode="after")
    def validate_settings(self) -> "Settings":
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
        if self.supabase_url:
            self.supabase_url = self.supabase_url.rstrip("/")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
