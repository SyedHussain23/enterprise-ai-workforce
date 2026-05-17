# ── Builder stage ─────────────────────────────────────────────────────────────
# python:3.12-slim keeps image lean (~130 MB base vs 900 MB full)
FROM python:3.12-slim AS builder

WORKDIR /app

# System deps needed by psycopg2 + chromadb C extensions
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# ── Runtime stage ──────────────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copy only the installed packages from builder
COPY --from=builder /install /usr/local

# Copy application source (excludes venv/, vector_db/ via .dockerignore)
COPY . .

# Pre-create runtime directories
RUN mkdir -p logs outputs vector_db

# Ensure the app package is always importable regardless of how Python is invoked
ENV PYTHONPATH=/app

EXPOSE 8000

# Healthcheck so Railway/Docker Compose know when the app is ready
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

# Production: run migrations then start
# $PORT is injected by Railway; default to 8000 locally
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.api.server:app --host 0.0.0.0 --port ${PORT:-8000} --workers 2"]
