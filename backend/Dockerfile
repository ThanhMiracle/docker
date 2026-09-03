FROM python:3.13-slim-bookworm AS builder

ARG DEBIAN_MIRROR=deb.debian.org
ARG NEED_BUILD_DEPS=0

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_INPUT=1

RUN set -eux; \
    apt-get update; \
    if [ "$NEED_BUILD_DEPS" = "1" ]; then \
        apt-get install -y --no-install-recommends build-essential; \
    fi; \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

ENV VENV_PATH=/opt/venv
RUN python -m venv "$VENV_PATH"

ENV PATH="$VENV_PATH/bin:$PATH"

COPY requirements.txt .

# Upgrade Python packaging tools to patched versions
RUN pip install --no-cache-dir --upgrade \
        pip \
        "setuptools>=78.1.1" \
    && pip install --no-cache-dir \
        --prefer-binary \
        -r requirements.txt

COPY app ./app


########################
# Runtime
########################

FROM python:3.13-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    VENV_PATH=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

RUN adduser --disabled-password --gecos "" appuser

WORKDIR /app

COPY --from=builder $VENV_PATH $VENV_PATH

COPY --chown=appuser:appuser app ./app

EXPOSE 8000

USER appuser

CMD [
    "uvicorn",
    "app.main:app",
    "--host", "0.0.0.0",
    "--port", "8000",
    "--workers", "1"
]


########################
# Test
########################

FROM runtime AS test

COPY --chown=appuser:appuser tests ./tests

CMD [
    "pytest",
    "-q",
    "-p", "no:cacheprovider",
    "/app/tests"
]