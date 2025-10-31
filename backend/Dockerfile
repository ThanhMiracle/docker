# syntax=docker/dockerfile:1.7

########################
# Stage 0: builder
########################
# Gợi ý dùng bookworm (ổn định, mirror tốt), vẫn là slim để nhỏ
FROM python:3.13-slim-bookworm AS builder

ARG DEBIAN_MIRROR=deb.debian.org
# Bật/ tắt toolchain build C (0: tắt, 1: bật)
ARG NEED_BUILD_DEPS=0

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    # Tăng tốc pip
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_INPUT=1

# (Tùy chọn) đổi mirror gần bạn để apt nhanh hơn
# Lưu ý: chỉ thay nếu cần. Có thể thử mirrors.ustc.edu.cn hoặc mirror.sjtu.edu.cn
# RUN sed -i "s|deb.debian.org|${DEBIAN_MIRROR}|g" /etc/apt/sources.list

# Cài toolchain CHỈ KHI thật sự cần (ví dụ có libs biên dịch C)
RUN --mount=type=cache,target=/var/cache/apt \
    set -eux; \
    apt-get update; \
    if [ "$NEED_BUILD_DEPS" = "1" ]; then \
      apt-get install -y --no-install-recommends build-essential; \
    fi; \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Tạo venv để copy sang runtime
ENV VENV_PATH=/opt/venv
RUN python -m venv "$VENV_PATH"
ENV PATH="$VENV_PATH/bin:$PATH"

# Chỉ copy requirements để tối đa cache
COPY requirements.txt .

# Ưu tiên wheel thay vì biên dịch: nhanh hơn rất nhiều
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip \
 && pip install --only-binary=:all: --prefer-binary -r requirements.txt \
    || pip install -r requirements.txt
    # Nếu có package không có wheel, dòng đầu sẽ fail và dòng sau fallback cài thường

# Copy source (không copy tests vào runtime để nhẹ)
COPY app ./app


########################
# Stage 1: runtime
########################
FROM python:3.13-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    VENV_PATH=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

# Tạo user không phải root
RUN adduser --disabled-password --gecos "" appuser

WORKDIR /app

# Copy venv từ builder
COPY --from=builder $VENV_PATH $VENV_PATH

# Copy code app (không mang tests)
COPY --chown=appuser:appuser app ./app

EXPOSE 8000
USER appuser

# Biến ENV để chỉnh uvicorn nếu cần
# ENV UVICORN_HOST=0.0.0.0 UVICORN_PORT=8000 UVICORN_WORKERS=1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
