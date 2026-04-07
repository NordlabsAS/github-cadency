FROM python:3.11-slim

RUN adduser --disabled-password --gecos '' appuser

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=appuser:appuser . .

ARG DEVPULSE_VERSION=0.0.0
ARG DEVPULSE_BUILD_NUMBER=0
ARG DEVPULSE_COMMIT_SHA=unknown
ARG DEVPULSE_DEPLOY_TIME=unknown

ENV DEVPULSE_VERSION=$DEVPULSE_VERSION
ENV DEVPULSE_BUILD_NUMBER=$DEVPULSE_BUILD_NUMBER
ENV DEVPULSE_COMMIT_SHA=$DEVPULSE_COMMIT_SHA
ENV DEVPULSE_DEPLOY_TIME=$DEVPULSE_DEPLOY_TIME

USER appuser

CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
