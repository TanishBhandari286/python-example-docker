"""Production entry point: `gunicorn wsgi:app` (config in gunicorn.conf.py)."""
from taskboard import create_app

app = create_app()
