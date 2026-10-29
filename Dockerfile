FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    DATA_DIR=/app/data \
    WORK_ROOT=/tmp/bezik-tiktokdl

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt \
    && python -m playwright install --with-deps firefox \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --uid 1000 bot && mkdir -p /app/data && chown bot:bot /app/data
COPY bot ./bot

USER bot
VOLUME ["/app/data"]
CMD ["python", "-m", "bot"]
