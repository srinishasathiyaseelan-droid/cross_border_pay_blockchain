# CrossPay production image.
# Same runtime as the Render blueprint (render.yaml): Python 3.12.10, pinned requirements, gunicorn with ONE worker.
# One worker on purpose: the live decision feed (SSE bus), the AI job queue and the rate limiter live in-process;
# threads give concurrency.
#
# Build:  docker build -t crosspay .
# Run:    docker run -p 8000:8000 -e SECRET_KEY=... -e LEDGER_SIGNING_KEY=... -v crosspay-data:/data crosspay
# Or:     docker compose up --build        (see docker-compose.yml and README "Run with Docker")

FROM python:3.12.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Dependencies first, so a code change does not reinstall them.
# requirements.txt pins scikit-learn 1.9.1: the model card refuses a model pickled with another version.
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Only what the running app reads: code, templates, static assets and the checksummed model files.
# (model/evaluation, tests, docs and design files stay out of the image; secrets are excluded by .dockerignore.)
COPY app.py ./
COPY crosspay ./crosspay
COPY templates ./templates
COPY static ./static
COPY model/random_forest_model.pkl model/model_card.json model/metrics.json ./model/

# Run as an unprivileged user. All writable state (SQLite DB, audit chain, ledger view, uploads) is on /data.
RUN useradd --create-home --uid 10001 crosspay \
    && mkdir -p /data/uploads /app/instance \
    && chown -R crosspay:crosspay /data /app/instance
USER crosspay

# Production defaults. SECRET_KEY and LEDGER_SIGNING_KEY are NOT baked in: prod refuses to start without them,
# so pass them at run time (docker run -e ... or an env file).
ENV CROSSPAY_ENV=prod \
    PORT=8000 \
    DB_PATH=/data/crosspay.db \
    LEDGER_PATH=/data/blockchain_ledger.json \
    UPLOAD_DIR=/data/uploads
VOLUME ["/data"]
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD python -c "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:%s/healthz' % os.environ.get('PORT', '8000'), timeout=4)" || exit 1

# create_app() reads CROSSPAY_ENV, so the same image runs prod (default) or demo.
CMD ["sh", "-c", "exec gunicorn --workers 1 --threads 16 --timeout 120 --bind 0.0.0.0:${PORT} 'crosspay:create_app()'"]
