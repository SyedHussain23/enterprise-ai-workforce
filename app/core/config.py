from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    # ── Application ─────────────────────────────────────────────────────────
    APP_NAME: str = "Enterprise AI Workforce"
    DEBUG: bool = False
    SECRET_KEY: str = "change-me-in-production-use-32-char-min"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480  # 8 hours — full enterprise work session

    # ── Database (async driver for app, sync for Alembic CLI) ───────────────
    # asyncpg is used by SQLAlchemy at runtime
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/enterprise_ai"
    # psycopg2 is used by Alembic CLI (env.py run_migrations_offline)
    DATABASE_URL_SYNC: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/enterprise_ai"

    # ── Redis ────────────────────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379"

    # ── OpenAI ───────────────────────────────────────────────────────────────
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o"

    # ── LangSmith (Day 38) ───────────────────────────────────────────────────
    LANGCHAIN_TRACING_V2: bool = False
    LANGCHAIN_API_KEY: str = ""
    LANGCHAIN_PROJECT: str = "enterprise-ai-workforce"

    # ── CORS ─────────────────────────────────────────────────────────────────
    # Comma-separated list of allowed origins in production.
    # Example: https://enterprise-ai-workforce.vercel.app,https://yourdomain.com
    ALLOWED_ORIGINS: str = ""

    # ── WhatsApp (Day 54) ─────────────────────────────────────────────────────
    WHATSAPP_TOKEN: str = ""              # Meta permanent system user token
    WHATSAPP_PHONE_NUMBER_ID: str = ""   # From Meta App → WhatsApp → Configuration
    WHATSAPP_VERIFY_TOKEN: str = "enterprise_ai_verify"  # Set same in Meta webhook config

    # ── Connection pool ──────────────────────────────────────────────────────
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_RECYCLE: int = 3600

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
