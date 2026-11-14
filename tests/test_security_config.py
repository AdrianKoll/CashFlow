"""Configuração de segurança: chave secreta, cookies e criação do administrador."""
import pytest
from werkzeug.security import check_password_hash

from app import create_app
from app.models import User
from tests.conftest import database_config


def _config(tmp_path):
    return database_config(tmp_path)


def test_producao_sem_chave_secreta_recusa_iniciar(monkeypatch, tmp_path):
    monkeypatch.setenv("CASHFLOW_ENV", "production")
    with pytest.raises(RuntimeError, match="CASHFLOW_SECRET_KEY"):
        create_app(_config(tmp_path))


def test_chave_secreta_vem_do_ambiente(monkeypatch, tmp_path):
    monkeypatch.setenv("CASHFLOW_ENV", "production")
    monkeypatch.setenv("CASHFLOW_SECRET_KEY", "test-secret-key-that-is-not-committed")
    app = create_app(_config(tmp_path))
    assert app.config["SECRET_KEY"] == "test-secret-key-that-is-not-committed"


def test_desenvolvimento_gera_chave_aleatoria_diferente_a_cada_inicio(tmp_path):
    first = create_app(_config(tmp_path)).config["SECRET_KEY"]
    second = create_app(_config(tmp_path)).config["SECRET_KEY"]
    assert first and second and first != second


def test_cookies_de_sessao_sao_httponly_e_samesite(tmp_path):
    app = create_app(_config(tmp_path))
    assert app.config["SESSION_COOKIE_HTTPONLY"] is True
    assert app.config["SESSION_COOKIE_SAMESITE"] == "Lax"
    assert app.config["SESSION_COOKIE_SECURE"] is False


def test_cookie_seguro_pode_ser_ativado_por_variavel(monkeypatch, tmp_path):
    monkeypatch.setenv("CASHFLOW_SESSION_COOKIE_SECURE", "true")
    app = create_app(_config(tmp_path))
    assert app.config["SESSION_COOKIE_SECURE"] is True


def test_sem_variaveis_de_admin_nenhum_usuario_e_criado(tmp_path):
    app = create_app(_config(tmp_path))
    with app.app_context():
        assert User.query.count() == 0


def test_admin_e_criado_com_senha_em_hash(monkeypatch, tmp_path):
    monkeypatch.setenv("CASHFLOW_ADMIN_USERNAME", "dono")
    monkeypatch.setenv("CASHFLOW_ADMIN_PASSWORD", "uma-senha-bem-longa-123")
    app = create_app(_config(tmp_path))
    with app.app_context():
        admin = User.query.filter_by(username="dono").one()
        assert admin.password_hash != "uma-senha-bem-longa-123"
        assert check_password_hash(admin.password_hash, "uma-senha-bem-longa-123")


def test_admin_com_senha_curta_e_recusado(monkeypatch, tmp_path):
    monkeypatch.setenv("CASHFLOW_ADMIN_USERNAME", "dono")
    monkeypatch.setenv("CASHFLOW_ADMIN_PASSWORD", "curta")
    with pytest.raises(RuntimeError, match="12 caracteres"):
        create_app(_config(tmp_path))


@pytest.mark.parametrize("uri", ["", "sqlite:///cashflow.sqlite3", "mysql://u:p@h/db"])
def test_banco_que_nao_e_postgresql_e_recusado(uri, tmp_path):
    with pytest.raises(RuntimeError, match="PostgreSQL"):
        create_app({"SQLALCHEMY_DATABASE_URI": uri})


def test_sem_url_do_banco_a_aplicacao_recusa_iniciar():
    with pytest.raises(RuntimeError, match="CASHFLOW_DATABASE_URI"):
        create_app({"SECRET_KEY": "x"})
