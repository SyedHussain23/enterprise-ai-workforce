from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
import secrets

_INSECURE_DEFAULTS = {
    "change-me-in-production-use-32-char-min",
    "secret",
    "changeme",
    "your-secret-key",
}


class Settings(BaseSettings):
    # ── Application ─────────────────────────────────────────────────────────
    APP_NAME: str = "Enterprise AI Workforce"
    APP_VERSION: str = "1.2.0"
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
    s = Settings()

    # ── Startup security validation ───────────────────────────────────────────
    # Crash immediately if the insecure default SECRET_KEY is used outside DEBUG.
    # In DEBUG mode we allow it with a loud warning so local dev still works.
    if s.SECRET_KEY in _INSECURE_DEFAULTS or len(s.SECRET_KEY) < 32:
        if not s.DEBUG:
            raise RuntimeError(
                "\n\n"
                "╔══════════════════════════════════════════════════════════════╗\n"
                "║           SECURITY ERROR — STARTUP ABORTED                  ║\n"
                "╠══════════════════════════════════════════════════════════════╣\n"
                "║  SECRET_KEY is using an insecure default or is too short.   ║\n"
                "║  Generate a secure key and set it in your environment:       ║\n"
                "║                                                              ║\n"
                f"║  Suggested key: {secrets.token_hex(32)[:46]}  ║\n"
                "║                                                              ║\n"
                "║  Railway: Settings → Variables → SECRET_KEY = <your key>    ║\n"
                "╚══════════════════════════════════════════════════════════════╝\n"
            )
        import warnings
        warnings.warn(
            "⚠️  SECRET_KEY is using an insecure default. "
            "This is fine for local development but MUST be changed before production deployment.",
            stacklevel=2,
        )

    # ── OPENAI_API_KEY must be set ────────────────────────────────────────────
    if not s.OPENAI_API_KEY and not s.DEBUG:
        raise RuntimeError(
            "OPENAI_API_KEY is not set. "
            "Set it in your Railway environment variables before starting the server."
        )

    return s


settings = get_settings()
