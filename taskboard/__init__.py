"""Taskboard: a small task-tracking JSON API.

Application factory pattern: `create_app()` builds the Flask app.
Production entry point is `wsgi:app` (see wsgi.py), served by gunicorn.
"""
import logging

from flask import Flask

from . import db
from .config import load_config
from .logging_setup import configure_logging
from .routes import bp


def create_app(overrides: dict | None = None) -> Flask:
    app = Flask(__name__)
    app.config.update(load_config())
    if overrides:
        app.config.update(overrides)

    configure_logging(app.config["LOG_LEVEL"])
    db.init_app(app)
    app.register_blueprint(bp)

    logging.getLogger(__name__).info(
        "taskboard started",
        extra={"app_env": app.config["APP_ENV"], "database": app.config["DATABASE_PATH"]},
    )
    return app
