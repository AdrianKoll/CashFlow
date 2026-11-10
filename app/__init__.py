from __future__ import annotations

import os
import secrets
from pathlib import Path

from flask import Flask
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv


db = SQLAlchemy()
login_manager = LoginManager()
load_dotenv()


def _secret_key() -> str:
    """Obtém a chave da aplicação sem manter segredos no código-fonte."""
    configured = os.getenv("CASHFLOW_SECRET_KEY")
    environment = os.getenv("CASHFLOW_ENV", "development").strip().lower()
    if configured:
        return configured
    if environment == "production":
        raise RuntimeError("CASHFLOW_SECRET_KEY deve ser configurada em produção.")
    return secrets.token_hex(32)


def create_app(test_config: dict | None = None) -> Flask:
    """Fábrica da aplicação.

    `test_config` permite sobrescrever configurações (usado pelos testes
    automatizados para apontar para um banco temporário).
    """
    app = Flask(__name__, template_folder="../templates", static_folder="../static")

    app.config["SECRET_KEY"] = _secret_key()
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
        "CASHFLOW_DATABASE_URI", "sqlite:///cashflow_dados.sqlite3"
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["SESSION_COOKIE_SECURE"] = (
        os.getenv("CASHFLOW_SESSION_COOKIE_SECURE", "false").strip().lower() == "true"
    )
    if test_config:
        app.config.update(test_config)

    Path(app.instance_path).mkdir(parents=True, exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"

    from .models import User

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    from .helpers import initials as initials_fn

    @app.template_global()
    def initials(name: str) -> str:
        return initials_fn(name)

    from .routes import register_blueprints
    register_blueprints(app)

    with app.app_context():
        from .database import seed_database
        seed_database()

    return app
