from functools import lru_cache

from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "CampusKart API"
    api_v1_prefix: str = "/api/v1"
    database_url: str = "mysql+pymysql://root:change-me@localhost:3306/campuskart"
    frontend_origins: list[str] = ["http://localhost:5173"]
    jwt_secret_key: SecretStr
    access_token_minutes: int = 15

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
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
