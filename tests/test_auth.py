"""Login, logout e proteção das rotas."""
import pytest

from app.models import AuditLog
from tests.conftest import TEST_PASSWORD, TEST_USERNAME

PROTECTED_PATHS = [
    "/",
    "/movimentacoes",
    "/relatorios",
    "/registros-fixos",
    "/configuracoes",
    "/sobre",
    "/api/transactions/",
    "/api/summary/",
    "/api/products/",
    "/api/fixed-records/",
    "/copia/baixar",
    "/relatorios/pdf",
]


def test_pagina_de_login_carrega(client):
    response = client.get("/login")
    assert response.status_code == 200
    assert "Acessar sistema" in response.get_data(as_text=True)


@pytest.mark.parametrize("path", PROTECTED_PATHS)
def test_rotas_protegidas_redirecionam_para_login(client, path):
    response = client.get(path)
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_login_com_senha_errada_mostra_erro(client, user_id):
    response = client.post("/login", data={"username": TEST_USERNAME, "password": "errada"})
    assert response.status_code == 200
    assert "Usuário ou senha inválidos." in response.get_data(as_text=True)


def test_login_com_usuario_inexistente_mostra_a_mesma_mensagem(client, user_id):
    response = client.post("/login", data={"username": "ninguem", "password": TEST_PASSWORD})
    assert response.status_code == 200
    assert "Usuário ou senha inválidos." in response.get_data(as_text=True)


def test_login_valido_redireciona_e_registra_auditoria(app, client, user_id):
    response = client.post(
        "/login", data={"username": TEST_USERNAME, "password": TEST_PASSWORD}
    )
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/")
    with app.app_context():
        assert AuditLog.query.filter_by(action="login", user_id=user_id).count() == 1
    assert client.get("/").status_code == 200


def test_usuario_autenticado_que_abre_login_vai_para_o_painel(auth_client):
    response = auth_client.get("/login")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/")


def test_logout_encerra_a_sessao(auth_client):
    assert auth_client.get("/").status_code == 200
    response = auth_client.get("/logout")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]
    assert auth_client.get("/").status_code == 302
