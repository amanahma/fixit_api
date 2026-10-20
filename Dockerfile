FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

WORKDIR /app

RUN adduser --disabled-password --gecos "" --uid 1000 appuser

COPY pyproject.toml README.md ./
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir .

COPY alembic.ini entrypoint.sh ./
COPY app ./app
COPY migrations ./migrations

RUN chmod +x entrypoint.sh \
    && chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

ENTRYPOINT ["./entrypoint.sh"]
