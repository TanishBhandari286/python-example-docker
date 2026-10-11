# Gunicorn reads this file automatically when it is in the working directory.
# DEVOPS: every value can be overridden with an env var, see DEVOPS_NOTES.md.
import os

bind = f"0.0.0.0:{os.environ.get('PORT', '8000')}"
workers = int(os.environ.get("WEB_CONCURRENCY", "2"))
threads = int(os.environ.get("GUNICORN_THREADS", "2"))
timeout = int(os.environ.get("GUNICORN_TIMEOUT", "30"))
# Seconds gunicorn waits for in-flight requests after SIGTERM before killing
# workers. Keep this BELOW the stop timeout of the runtime (docker stop: 10s).
graceful_timeout = int(os.environ.get("GUNICORN_GRACEFUL_TIMEOUT", "8"))

# Access + error logs to stdout/stderr, never to files.
accesslog = "-"
errorlog = "-"
loglevel = os.environ.get("LOG_LEVEL", "info").lower()
