# syntax=docker/dockerfile:1
#
# Taskboard: production image (single-stage).
# Every choice here maps to a line in DEVOPS_NOTES.md (§ numbers in comments).
#
# Build:  docker build -t taskboard:1.0 --build-arg APP_VERSION=$(git rev-parse --short HEAD) .
# Run:    docker run -d --name taskboard -p 8000:8000 \
#           -e SECRET_KEY=... -v taskboard-data:/data taskboard:1.0

# ── 1. Base image ─────────────────────────────────────────────────────────
# §2: Python 3.12, no OS packages needed → the slim variant is enough.
# Tag pinned to the minor version: we get 3.12.x security patches on rebuild,
# but never a surprise jump to 3.13.
FROM python:3.12-slim

# ── 2. Python-in-a-container settings (§4) ────────────────────────────────
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# ── 3. Unprivileged user + writable data dir (§2, §5) ─────────────────────
# Changes almost never → near the top so it stays cached.
# Fixed UID/GID (10001) so volume ownership is predictable across rebuilds.
# /data is owned by app: a NEW named volume mounted there copies this
# ownership, so the non-root app can write its SQLite file.
RUN groupadd --system --gid 10001 app \
 && useradd --system --uid 10001 --gid app --no-create-home --shell /usr/sbin/nologin app \
 && mkdir /data \
 && chown app:app /data

WORKDIR /app

# ── 4. Dependencies: manifest first, then install (§2) ────────────────────
# This layer is rebuilt ONLY when requirements.txt changes.
# requirements-dev.txt is deliberately NOT installed (no pytest in prod).
COPY requirements.txt .
RUN pip install -r requirements.txt

# ── 5. Application code: changes every commit → LAST of the slow parts (§3)
# Only the three things the app needs. Owned by root and read-only for the
# app user: a compromised app can't rewrite its own code.
COPY taskboard/ ./taskboard/
COPY wsgi.py gunicorn.conf.py ./

# ── 6. Runtime configuration (§4) ─────────────────────────────────────────
# Non-secret defaults only. SECRET_KEY is NOT here: it's injected at runtime.
ENV APP_ENV=production \
    DATABASE_PATH=/data/taskboard.db \
    PORT=8000

# Version stamp (§4: "set at build time"). ARG goes this low because a new
# value busts the cache for every step after it. Down here that's only
# metadata, so it costs nothing.
ARG APP_VERSION=dev
ENV APP_VERSION=${APP_VERSION}

# ── 7. Drop privileges (§2) ───────────────────────────────────────────────
USER app

# ── 8. Metadata ───────────────────────────────────────────────────────────
# Documentation only: `docker run -p` is what actually publishes the port.
EXPOSE 8000

# §6: no curl in the image, so use Python. Exec form; exits non-zero
# (an exception) if /healthz doesn't answer within 2s.
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD ["python", "-c", "import os, urllib.request as u; u.urlopen('http://127.0.0.1:%s/healthz' % os.environ.get('PORT', '8000'), timeout=2)"]

# §8: exec form → gunicorn is PID 1 and gets SIGTERM for a graceful stop.
# gunicorn auto-loads ./gunicorn.conf.py (bind 0.0.0.0:$PORT, logs to stdout).
CMD ["gunicorn", "wsgi:app"]
