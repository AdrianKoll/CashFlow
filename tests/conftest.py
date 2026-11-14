"""Fixtures compartilhadas pelos testes do CashFlow.

Cada teste recebe uma aplicação nova, com banco SQLite temporário e diretório
de cópias de segurança temporário, sem tocar em dados reais.
"""
import os
import uuid

import pytest
import sqlalchemy as sa
from werkzeug.security import generate_password_hash

from app import create_app, db
from app.models import User

TEST_USERNAME = "tester"
TEST_PASSWORD = "senha-de-teste-123"

# Para rodar a suíte contra PostgreSQL, defina TEST_DATABASE_URL, por exemplo:
#   TEST_DATABASE_URL=postgresql+psycopg://usuario:senha@localhost:5432/cashflow_test
# Cada teste usa um schema próprio, apagado ao final. Sem a variável, os testes
# usam um arquivo SQLite temporário.
TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL", "").strip()
USING_POSTGRES = TEST_DATABASE_URL.startswith(("postgresql", "postgres"))

_created_apps: list = []
_postgres_schemas: list[str] = []


@pytest.fixture(autouse=True)
def clean_environment(monkeypatch):
    """Remove variáveis que um .env local poderia injetar nos testes."""
    for name in (
        "CASHFLOW_ENV",
        "CASHFLOW_SECRET_KEY",
        "CASHFLOW_ADMIN_NAME",
        "CASHFLOW_ADMIN_USERNAME",
        "CASHFLOW_ADMIN_PASSWORD",
        "CASHFLOW_SESSION_COOKIE_SECURE",
        "CASHFLOW_DATABASE_URI",
    ):
        monkeypatch.delenv(name, raising=False)


def database_config(tmp_path) -> dict:
    """Configuração do banco do teste: SQLite temporário ou um schema novo no PostgreSQL."""
    if not USING_POSTGRES:
        return {"SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path / 'test.sqlite3'}"}
    schema = f"t_{uuid.uuid4().hex[:12]}"
    engine = sa.create_engine(TEST_DATABASE_URL)
    with engine.begin() as connection:
        connection.execute(sa.text(f'CREATE SCHEMA "{schema}"'))
    engine.dispose()
    _postgres_schemas.append(schema)
    return {
        "SQLALCHEMY_DATABASE_URI": TEST_DATABASE_URL,
        "SQLALCHEMY_ENGINE_OPTIONS": {"connect_args": {"options": f"-csearch_path={schema}"}},
    }


@pytest.fixture(autouse=True)
def release_databases():
    """Fecha as conexões de cada app e apaga os schemas criados pelo teste."""
    yield
    while _created_apps:
        flask_app = _created_apps.pop()
        with flask_app.app_context():
            db.session.remove()
            db.engine.dispose()
    if _postgres_schemas:
        engine = sa.create_engine(TEST_DATABASE_URL)
        with engine.begin() as connection:
            for schema in _postgres_schemas:
                connection.execute(sa.text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
        engine.dispose()
        _postgres_schemas.clear()


def make_app(tmp_path, **extra_config):
    config = {
        "TESTING": True,
        "SECRET_KEY": "test-secret-key-that-is-not-committed",
        **database_config(tmp_path),
        # Desligado por padrão para não poluir os demais testes; tests/test_csrf.py
        # liga explicitamente (WTF_CSRF_ENABLED=True).
        "WTF_CSRF_ENABLED": False,
        # Idem para o limite de tentativas; tests/test_rate_limit.py liga.
        "RATELIMIT_ENABLED": False,
    }
    config.update(extra_config)
    flask_app = create_app(config)
    _created_apps.append(flask_app)
    # As cópias de segurança vão para uma pasta temporária, não para o projeto.
    flask_app.instance_path = str(tmp_path / "instance")
    return flask_app


@pytest.fixture()
def app(tmp_path):
    return make_app(tmp_path)


@pytest.fixture()
def client(app):
    return app.test_client()


def create_test_user(app, username=TEST_USERNAME, password=TEST_PASSWORD):
    with app.app_context():
        user = User(
            name="Usuário de Teste",
            username=username,
            role="Administrador",
            password_hash=generate_password_hash(password),
        )
        db.session.add(user)
        db.session.commit()
        return user.id


@pytest.fixture()
def user_id(app):
    return create_test_user(app)


@pytest.fixture()
def auth_client(app, user_id):
    """Cliente já autenticado (sessão criada direto, sem passar pelo /login)."""
    client = app.test_client()
    with client.session_transaction() as session:
        session["_user_id"] = str(user_id)
        session["_fresh"] = True
    return client
