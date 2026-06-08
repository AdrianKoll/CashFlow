from __future__ import annotations
from pathlib import Path
from flask import Flask
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
login_manager = LoginManager()


def create_app() -> Flask:
    app = Flask(__name__, template_folder="../templates", static_folder="../static")

    app.config["SECRET_KEY"] = "cashflow-local-key-2026"
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///cashflow_dados.sqlite3"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

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

    # Cria tabelas e popula dados iniciais dentro do contexto da aplicação
    with app.app_context():
        from .database import seed_database
        seed_database()

    return app
