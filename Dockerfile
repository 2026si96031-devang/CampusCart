FROM python:3.12-slim AS builder
WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.12-slim
RUN apt-get update \
    && apt-get upgrade -y \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --system --uid 10001 --create-home appuser
COPY --from=builder /install /usr/local
WORKDIR /app
COPY app.py .
ARG APP_VERSION=1.0.0
ARG BROKEN=false
ENV APP_VERSION=${APP_VERSION} \
    BROKEN=${BROKEN} \
    PYTHONUNBUFFERED=1
USER appuser
EXPOSE 8080
HEALTHCHECK --interval=10s --timeout=3s --retries=3 CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')"
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "2", "app:app"]
