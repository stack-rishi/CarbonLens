import os
import warnings

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # App Settings
    PROJECT_NAME: str = "CarbonLens"
    ENVIRONMENT: str = "development"
    SECRET_KEY: str = ""
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 120  # 2 hours (reduced from 24h for security)

    # Supabase Settings
    SUPABASE_URL: str = ""
    SUPABASE_ANON_KEY: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""

    # AI Integration Settings
    GROQ_API_KEY: str = ""
    ANTHROPIC_API_KEY: str | None = None

    # Database Settings
    DATABASE_URL: str = ""

    # Frontend Settings
    FRONTEND_URL: str = "http://localhost:5173"

    model_config = SettingsConfigDict(
        env_file=os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            ".env",
        ),
        env_file_encoding="utf-8",
        extra="ignore",
    )


# Instantiate settings
settings = Settings(**{})

# --- Startup Validation ---
# Fail fast if SECRET_KEY is empty or a known default
_UNSAFE_SECRETS = {
    "",
    "super-secret-key-for-local-jwt",
    "your-super-secret-jwt-key-change-in-production",
    "changeme",
}

if settings.ENVIRONMENT == "production":
    if settings.SECRET_KEY in _UNSAFE_SECRETS:
        raise RuntimeError(
            "CRITICAL: SECRET_KEY is empty or using a default value. "
            "Set a strong, random SECRET_KEY before running in production."
        )
    if not settings.DATABASE_URL:
        raise RuntimeError(
            "CRITICAL: DATABASE_URL is not set. Cannot start in production without a database."
        )
    if not settings.SUPABASE_URL:
        raise RuntimeError(
            "CRITICAL: SUPABASE_URL is not set. Cannot start in production without Supabase."
        )
elif settings.SECRET_KEY in _UNSAFE_SECRETS:
    warnings.warn(
        "SECRET_KEY is empty or using a default value. "
        "This is acceptable for local development only.",
        stacklevel=2,
    )
