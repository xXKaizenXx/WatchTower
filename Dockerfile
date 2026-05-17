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

RUN pip install --no-cache-dir . \
    && sed -i 's/\r$//' /entrypoint.sh \
    && chmod +x /entrypoint.sh \
    && chown watchtower:watchtower /entrypoint.sh \
    && chown -R watchtower:watchtower /app

USER watchtower
EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
