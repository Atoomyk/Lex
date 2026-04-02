import os

from flask import Flask

from db import create_db
from routes import register_routes

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    def load_dotenv():
        return False


def _as_bool(value: str, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def create_app() -> Flask:
    load_dotenv()
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "change-me-secret-key")
    # Two fixed accounts (admin + user) stored in .env.
    # Backward compatible with APP_USERNAME / APP_PASSWORD_HASH if provided.
    app.config["ADMIN_USERNAME"] = os.getenv("ADMIN_USERNAME", "")
    app.config["ADMIN_PASSWORD_HASH"] = os.getenv("ADMIN_PASSWORD_HASH", "")
    app.config["USER_USERNAME"] = os.getenv("USER_USERNAME", "")
    app.config["USER_PASSWORD_HASH"] = os.getenv("USER_PASSWORD_HASH", "")
    app.config["APP_USERNAME"] = os.getenv("APP_USERNAME", "")
    app.config["APP_PASSWORD_HASH"] = os.getenv("APP_PASSWORD_HASH", "")
    create_db()
    register_routes(app)
    return app


app = create_app()


if __name__ == "__main__":
    host = os.getenv("APP_HOST", "0.0.0.0")
    port = int(os.getenv("APP_PORT", "5001"))
    debug = _as_bool(os.getenv("APP_DEBUG"), default=False)
    app.run(host=host, port=port, debug=debug)