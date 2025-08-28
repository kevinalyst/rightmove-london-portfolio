# Playwright-friendly Python base
FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    POETRY_VIRTUALENVS_CREATE=false

WORKDIR /app

# System deps (minimal; base already contains browsers and fonts)
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Project files and source
COPY pyproject.toml README.md ./
COPY src ./src
COPY jobs ./jobs
COPY jobs/shards /app/shards

# Install Python deps and Playwright browsers and system deps
RUN pip install --upgrade pip && \
    pip install . && \
    python -m playwright install --with-deps

# Provide default shards directory (mounted/overridden at runtime)
RUN mkdir -p /app/shards /workspace/out

# Optional: google-cloud-storage if uploading outputs to GCS
RUN pip install google-cloud-storage

# Default environment
ENV OUTPUT_DIR=/workspace/out \
    SHARDS_DIR=/app/shards \
    MAX_CONCURRENCY=1 \
    HEADLESS=true \
    REQUEST_TIMEOUT=45

# Health check (basic)
HEALTHCHECK CMD python -c "import sys; sys.exit(0)" || exit 1

# Entry point for Cloud Run Job
ENTRYPOINT ["python", "jobs/entrypoint.py"]


