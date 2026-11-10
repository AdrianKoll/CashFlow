"""Fixtures compartilhadas pelos testes do CashFlow.

Cada teste recebe uma aplicação nova, com banco SQLite temporário e diretório
de cópias de segurança temporário, sem tocar em dados reais.
"""
import pytest
from werkzeug.security import generate_password_hash

from app import create_app, db
from app.models import User

TEST_USERNAME = "tester"
TEST_PASSWORD = "senha-de-teste-123"


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


def make_app(tmp_path, **extra_config):
    config = {
        "TESTING": True,
        "SECRET_KEY": "test-secret-key-that-is-not-committed",
        "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path / 'test.sqlite3'}",
        # Desligado por padrão para não poluir os demais testes; tests/test_csrf.py
        # liga explicitamente (WTF_CSRF_ENABLED=True).
        "WTF_CSRF_ENABLED": False,
    }
    config.update(extra_config)
    flask_app = create_app(config)
    # As cópias de segurança vão para uma pasta temporária, não para o projeto.
    flask_app.instance_path = str(tmp_path / "instance")
    return flask_app


@pytest.fixture()
def app(tmp_path):
    return make_app(tmp_path)


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def user_id(app):
    with app.app_context():
        user = User(
            name="Usuário de Teste",
            username=TEST_USERNAME,
            role="Administrador",
            password_hash=generate_password_hash(TEST_PASSWORD),
        )
        db.session.add(user)
        db.session.commit()
        return user.id


@pytest.fixture()
def auth_client(app, user_id):
    """Cliente já autenticado (sessão criada direto, sem passar pelo /login)."""
    client = app.test_client()
    with client.session_transaction() as session:
        session["_user_id"] = str(user_id)
        session["_fresh"] = True
    return client
