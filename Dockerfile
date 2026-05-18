FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN groupadd --gid 1000 watchtower \
    && useradd --uid 1000 --gid watchtower --create-home watchtower

WORKDIR /app

COPY pyproject.toml .
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini .
COPY scripts/entrypoint.sh /entrypoint.sh

COPY scripts/start-api.sh /start-api.sh

RUN pip install --no-cache-dir . \
    && sed -i 's/\r$//' /entrypoint.sh /start-api.sh \
    && chmod +x /entrypoint.sh /start-api.sh \
    && chown watchtower:watchtower /entrypoint.sh /start-api.sh \
    && chown -R watchtower:watchtower /app

USER watchtower
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')" || exit 1

ENV PORT=8000

ENTRYPOINT ["/entrypoint.sh"]
CMD ["/start-api.sh"]
