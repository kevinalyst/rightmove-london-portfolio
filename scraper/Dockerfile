FROM python:3.11-slim-bookworm

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml README.md /app/
COPY src /app/src

RUN pip install -U pip && pip install -e '.[dev]' && \
    python -m playwright install --with-deps

ENTRYPOINT ["python", "-m", "rightmove_scraper.cli"]

