"""Application configuration.

Everything the app needs to be told about its environment lives here, read from
environment variables with sensible local defaults so the project runs with no setup.
"""

import os

# Absolute path to the project root (one level above this file's package).
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# The instance folder holds everything generated at runtime: the SQLite database,
# the mail outbox and the CSV exports. It is git-ignored.
INSTANCE_DIR = os.path.join(BASE_DIR, "instance")


class Config:
    # Used by Flask to sign the session cookie. Override in production.
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-me")

    # --- Database -------------------------------------------------------
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", "sqlite:///" + os.path.join(INSTANCE_DIR, "tma.db")
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # --- Redis ----------------------------------------------------------
    REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

    # Celery uses separate Redis databases so that flushing the cache during a
    # demo cannot destroy queued tasks.
    CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/1")
    CELERY_RESULT_BACKEND = os.environ.get(
        "CELERY_RESULT_BACKEND", "redis://localhost:6379/2"
    )

    # --- Cache TTLs (seconds) -------------------------------------------
    CACHE_TTL_TREKS = 60
    CACHE_TTL_STATS = 30

    # --- Mail -----------------------------------------------------------
    # "file"  -> write each message as an HTML file into instance/outbox/
    # "smtp"  -> send through a real SMTP server
    # The file backend is the default because it needs no mail server, works
    # offline, and leaves an artefact that can be opened during the demo.
    MAIL_BACKEND = os.environ.get("MAIL_BACKEND", "file")
    MAIL_SERVER = os.environ.get("MAIL_SERVER", "localhost")
    MAIL_PORT = int(os.environ.get("MAIL_PORT", 1025))
    MAIL_SENDER = os.environ.get("MAIL_SENDER", "noreply@tma.local")

    OUTBOX_DIR = os.path.join(INSTANCE_DIR, "outbox")
    EXPORT_DIR = os.path.join(INSTANCE_DIR, "exports")

    # --- Seed admin -----------------------------------------------------
    # The single administrator, created programmatically by `flask seed`.
    # The problem statement forbids admin registration.
    ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@tma.local")
    ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")

    # --- Pagination -----------------------------------------------------
    PAGE_SIZE = 6
