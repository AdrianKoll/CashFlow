from __future__ import annotations

import os
import secrets
from pathlib import Path

from flask import Flask, flash, jsonify, make_response, redirect, render_template, request, url_for
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_login import LoginManager, current_user
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFError, CSRFProtect
from werkzeug.middleware.proxy_fix import ProxyFix
from dotenv import load_dotenv


db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()
# Os limites são declarados por rota (ex.: login). Sem limites padrão globais.
limiter = Limiter(key_func=get_remote_address)
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


def normalize_database_uri(uri: str) -> str:
    """Padroniza a URL do banco.

    Provedores como Heroku e Render entregam "postgres://", e o SQLAlchemy
    exige "postgresql://". Este projeto usa o driver psycopg (versão 3).
    """
    for prefix in ("postgres://", "postgresql://"):
        if uri.startswith(prefix):
            return "postgresql+psycopg://" + uri[len(prefix):]
    return uri


def _trusted_proxies() -> int:
    raw = os.getenv("CASHFLOW_TRUSTED_PROXIES", "0").strip()
    return int(raw) if raw.isdigit() else 0


def create_app(test_config: dict | None = None) -> Flask:
    """Fábrica da aplicação.

    `test_config` permite sobrescrever configurações (usado pelos testes
    automatizados para apontar para um banco temporário).
    """
    app = Flask(__name__, template_folder="../templates", static_folder="../static")

    app.config["SECRET_KEY"] = _secret_key()
    app.config["SQLALCHEMY_DATABASE_URI"] = normalize_database_uri(
        os.getenv("CASHFLOW_DATABASE_URI", "").strip()
    )
    # Testa a conexão antes de usá-la: evita erro após reinício do banco.
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {"pool_pre_ping": True}
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["SESSION_COOKIE_SECURE"] = (
        os.getenv("CASHFLOW_SESSION_COOKIE_SECURE", "false").strip().lower() == "true"
    )
    # O token CSRF vale enquanto a sessão existir (evita erro em abas abertas).
    app.config["WTF_CSRF_TIME_LIMIT"] = None
    # Limite de tentativas: em memória por padrão (um contador por processo).
    # Com vários workers, aponte para um armazenamento compartilhado, como Redis.
    app.config["RATELIMIT_STORAGE_URI"] = os.getenv("CASHFLOW_RATELIMIT_STORAGE_URI", "memory://")
    app.config["RATELIMIT_HEADERS_ENABLED"] = True
    # Quantos proxies reversos confiáveis existem na frente da aplicação.
    # 0 (padrão) ignora X-Forwarded-For, que qualquer cliente pode forjar.
    app.config["TRUSTED_PROXIES"] = _trusted_proxies()
    if test_config:
        app.config.update(test_config)

    if not app.config["SQLALCHEMY_DATABASE_URI"].startswith("postgresql"):
        raise RuntimeError(
            "CASHFLOW_DATABASE_URI deve apontar para um PostgreSQL, por exemplo "
            "postgresql://usuario:senha@localhost:5432/cashflow."
        )

    if app.config["TRUSTED_PROXIES"] > 0:
        hops = app.config["TRUSTED_PROXIES"]
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=hops, x_proto=hops, x_host=hops)

    Path(app.instance_path).mkdir(parents=True, exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    csrf.init_app(app)
    limiter.init_app(app)

    @app.errorhandler(429)
    def handle_rate_limit(error):
        message = "Muitas tentativas. Aguarde alguns minutos e tente novamente."
        if request.path.startswith("/api/"):
            return jsonify({"error": message}), 429
        return make_response(render_template("login.html", error=message), 429)

    @app.errorhandler(CSRFError)
    def handle_csrf_error(error):
        message = "Sessão expirada ou requisição inválida. Recarregue a página e tente novamente."
        if request.path.startswith("/api/"):
            return jsonify({"error": message}), 400
        if current_user.is_authenticated:
            flash(message, "error")
            return redirect(url_for("pages.dashboard"))
        return render_template("login.html", error=message), 400

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
