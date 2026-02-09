"""Configuration management using pydantic-settings."""

from pydantic_settings import BaseSettings
from pydantic import Field
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Anthropic
    anthropic_api_key: str = Field(..., description="Anthropic API key")

    # Email (Resend)
    resend_api_key: str = Field(..., description="Resend API key")
    from_email: str = Field(
        default="noreply@yourdomain.com", description="Sender email"
    )
    approval_email: str = Field(
        default="nitesh@themindfulinitiative.com",
        description="Nitesh's email for approvals",
    )

    # Instagram
    instagram_access_token: str = Field(
        default="", description="Instagram Graph API long-lived token"
    )
    instagram_account_id: str = Field(
        default="", description="Instagram Business Account ID"
    )

    # Server
    server_base_url: str = Field(
        default="http://localhost:8000", description="Public URL of the webhook server"
    )
    server_port: int = Field(default=8000, description="Server port")
    secret_key: str = Field(
        default="change-this-to-a-random-string",
        description="Secret for signing approval tokens",
    )

    # Scheduler
    post_generation_hour: int = Field(
        default=7, description="Hour to generate posts (24h format)"
    )
    post_generation_minute: int = Field(
        default=0, description="Minute to generate posts"
    )
    timezone: str = Field(default="Asia/Kolkata", description="Timezone")

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    # Database
    database_url: str = Field(
        default="", description="Postgres connection URL (e.g. from Neon). If empty, uses local SQLite."
    )


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
