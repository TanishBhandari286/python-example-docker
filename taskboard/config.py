"""All runtime configuration comes from environment variables.

DEVOPS: this file is the source of truth for env vars. See DEVOPS_NOTES.md
for the table of what to set in each environment.
"""
import os


class ConfigError(RuntimeError):
    pass


def load_config() -> dict:
    app_env = os.environ.get("APP_ENV", "development")

    secret_key = os.environ.get("SECRET_KEY")
    if not secret_key:
        if app_env == "production":
            # Fail fast: better to crash on boot than to run prod with a
            # guessable key.
            raise ConfigError("SECRET_KEY must be set when APP_ENV=production")
        secret_key = "dev-only-not-secret"

    return {
        "APP_ENV": app_env,
        "SECRET_KEY": secret_key,
        "LOG_LEVEL": os.environ.get("LOG_LEVEL", "INFO").upper(),
        # The app WRITES here. In a container this must be on a volume or
        # the data is gone when the container is removed.
        "DATABASE_PATH": os.environ.get("DATABASE_PATH", "./data/taskboard.db"),
        "APP_VERSION": os.environ.get("APP_VERSION", "dev"),
    }
