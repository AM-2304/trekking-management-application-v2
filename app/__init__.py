"""Application factory.

`create_app()` builds and configures the Flask application. Keeping this in a function
rather than at module level means the test suite can build a second, independent app
pointed at an in-memory database.
"""

import os

from flask import Flask, render_template
from sqlalchemy import event
from sqlalchemy.engine import Engine

from .config import Config, INSTANCE_DIR
from .models import db


@event.listens_for(Engine, "connect")
def _set_sqlite_pragmas(dbapi_connection, connection_record):
    """Configure every new SQLite connection.

    foreign_keys  - SQLite defaults this to OFF, which would make every FOREIGN KEY in
                    models.py decorative. This turns real referential integrity on.
    journal_mode  - WAL lets readers carry on while a write is in progress, so a booking
                    does not block every dashboard query.
    busy_timeout  - concurrent writers wait their turn instead of failing instantly.
    """
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA busy_timeout=5000")
    cursor.close()


def create_app(config_object=Config):
    app = Flask(__name__, instance_relative_config=False)
    app.config.from_object(config_object)

    # Make sure the runtime folders exist before anything tries to write to them.
    for folder in (INSTANCE_DIR, app.config["OUTBOX_DIR"], app.config["EXPORT_DIR"]):
        os.makedirs(folder, exist_ok=True)

    db.init_app(app)

    # Blueprints
    from .auth import auth_bp
    from .routes_admin import admin_bp
    from .routes_staff import staff_bp
    from .routes_user import user_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(staff_bp)
    app.register_blueprint(user_bp)

    # The single Jinja2 template, used only as the entry point for the Vue app.
    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/api/health")
    def health():
        return {"status": "ok"}

    # Point Celery at Redis from inside the web process too.
    # Without this, calling task.delay() from a route would try to reach Celery's
    # default broker (RabbitMQ) instead of Redis and fail with "connection refused".
    from .tasks import init_celery

    init_celery(app)

    # CLI commands: `flask --app run.py init-db` and `flask --app run.py seed`
    from .seed import register_cli

    register_cli(app)

    return app
