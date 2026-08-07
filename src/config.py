"""Configuration management using pydantic-settings."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Anthropic
    anthropic_api_key: str = Field(default="", description="Anthropic API key")

    # Email (Resend)
    resend_api_key: str = Field(default="", description="Resend API key")
    from_email: str = Field(
        default="noreply@yourdomain.com", description="Sender email"
    )
    approval_email: str = Field(
        default="nitesh@themindfulinitiative.com",
        description="Approver email(s), comma-separated",
    )

    @property
    def approval_email_list(self) -> list[str]:
        return [e.strip() for e in self.approval_email.split(",") if e.strip()]

    # Instagram
    instagram_access_token: str = Field(
        default="", description="Instagram Graph API long-lived token"
    )
    instagram_account_id: str = Field(
        default="", description="Instagram Business Account ID"
    )

    # LinkedIn
    linkedin_access_token: str = Field(
        default="", description="LinkedIn OAuth token with w_organization_social"
    )
    linkedin_organization_id: str = Field(
        default="", description="Numeric ID of the LinkedIn company page"
    )

    # OpenAI image generation
    openai_api_key: str = Field(
        default="", description="OpenAI API key used for branded backgrounds"
    )
    openai_image_model: str = Field(
        default="gpt-image-2", description="OpenAI image-generation model"
    )
    openai_image_quality: str = Field(
        default="medium", description="Image quality: low, medium, high, or auto"
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

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }

    # Database
    database_url: str = Field(
        default="", description="Postgres connection URL (e.g. from Neon). If empty, uses local SQLite."
    )


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
