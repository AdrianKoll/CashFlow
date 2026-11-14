"""Proteção CSRF em formulários HTML e na API JSON."""
import re
from pathlib import Path

import pytest
from werkzeug.security import check_password_hash

from app import db
from app.models import Transaction, User
from tests.conftest import TEST_PASSWORD, TEST_USERNAME, make_app

TEMPLATES = Path(__file__).resolve().parent.parent / "templates"
FORM_RE = re.compile(r"<form\b[^>]*>.*?</form>", re.DOTALL | re.IGNORECASE)


@pytest.fixture()
def csrf_app(tmp_path):
    return make_app(tmp_path, WTF_CSRF_ENABLED=True)


@pytest.fixture()
def csrf_auth_client(csrf_app, user_id_for):
    client = csrf_app.test_client()
    with client.session_transaction() as session:
        session["_user_id"] = str(user_id_for)
        session["_fresh"] = True
    return client


@pytest.fixture()
def user_id_for(csrf_app):
    from werkzeug.security import generate_password_hash

    with csrf_app.app_context():
        user = User(
            name="Teste",
            username=TEST_USERNAME,
            password_hash=generate_password_hash(TEST_PASSWORD),
        )
        db.session.add(user)
        db.session.commit()
        return user.id


def _meta_token(client):
    html = client.get("/").get_data(as_text=True)
    match = re.search(r'<meta name="csrf-token" content="([^"]+)"', html)
    assert match, "a página deve expor o token CSRF para o JavaScript"
    return match.group(1)


def _form_token(client, path="/login"):
    html = client.get(path).get_data(as_text=True)
    match = re.search(r'name="csrf_token" value="([^"]+)"', html)
    assert match, f"formulário de {path} sem token CSRF"
    return match.group(1)


# --- Formulários HTML -------------------------------------------------------

def test_login_sem_token_e_recusado(csrf_app, user_id_for):
    client = csrf_app.test_client()
    response = client.post("/login", data={"username": TEST_USERNAME, "password": TEST_PASSWORD})
    assert response.status_code == 400
    assert "Sessão expirada ou requisição inválida" in response.get_data(as_text=True)
    assert client.get("/").status_code == 302  # continua sem sessão


def test_login_com_token_funciona(csrf_app, user_id_for):
    client = csrf_app.test_client()
    token = _form_token(client)
    response = client.post(
        "/login",
        data={"username": TEST_USERNAME, "password": TEST_PASSWORD, "csrf_token": token},
    )
    assert response.status_code == 302
    assert client.get("/").status_code == 200


def test_troca_de_senha_sem_token_nao_altera_a_senha(csrf_app, csrf_auth_client, user_id_for):
    response = csrf_auth_client.post(
        "/configuracoes/senha",
        data={
            "current_password": TEST_PASSWORD,
            "new_password": "senha-invasora-1",
            "confirm_password": "senha-invasora-1",
        },
        follow_redirects=True,
    )
    assert "Sessão expirada ou requisição inválida" in response.get_data(as_text=True)
    with csrf_app.app_context():
        user = db.session.get(User, user_id_for)
        assert check_password_hash(user.password_hash, TEST_PASSWORD)


def test_troca_de_senha_com_token_funciona(csrf_app, csrf_auth_client, user_id_for):
    token = _form_token(csrf_auth_client, "/configuracoes")
    response = csrf_auth_client.post(
        "/configuracoes/senha",
        data={
            "current_password": TEST_PASSWORD,
            "new_password": "senha-nova-valida-1",
            "confirm_password": "senha-nova-valida-1",
            "csrf_token": token,
        },
        follow_redirects=True,
    )
    assert "Senha alterada com sucesso." in response.get_data(as_text=True)


def test_criar_copia_sem_token_e_recusado(csrf_app, csrf_auth_client):
    response = csrf_auth_client.post("/copia/criar")
    assert response.status_code == 302
    copias = Path(csrf_app.instance_path) / "copias"
    assert not copias.exists() or not list(copias.glob("*.dump"))


# --- API JSON (token no cabeçalho X-CSRFToken) ---------------------------------

PAYLOAD = {"kind": "entrada", "title": "Venda", "amount": 10}


def test_api_post_sem_cabecalho_e_recusada_com_json(csrf_app, csrf_auth_client):
    response = csrf_auth_client.post("/api/transactions/", json=PAYLOAD)
    assert response.status_code == 400
    assert "Recarregue a página" in response.get_json()["error"]
    with csrf_app.app_context():
        assert Transaction.query.count() == 0


def test_api_post_com_cabecalho_funciona(csrf_app, csrf_auth_client):
    token = _meta_token(csrf_auth_client)
    response = csrf_auth_client.post(
        "/api/transactions/", json=PAYLOAD, headers={"X-CSRFToken": token}
    )
    assert response.status_code == 201


def test_api_patch_e_delete_sem_token_sao_recusados(csrf_app, csrf_auth_client):
    token = _meta_token(csrf_auth_client)
    tx_id = csrf_auth_client.post(
        "/api/transactions/", json=PAYLOAD, headers={"X-CSRFToken": token}
    ).get_json()["id"]

    assert csrf_auth_client.patch(f"/api/transactions/{tx_id}", json={"amount": 999}).status_code == 400
    assert csrf_auth_client.delete(f"/api/transactions/{tx_id}").status_code == 400
    with csrf_app.app_context():
        tx = db.session.get(Transaction, tx_id)
        assert tx is not None and tx.amount == 10


def test_reset_de_dados_exige_token(csrf_app, csrf_auth_client):
    token = _meta_token(csrf_auth_client)
    csrf_auth_client.post("/api/transactions/", json=PAYLOAD, headers={"X-CSRFToken": token})
    response = csrf_auth_client.post("/api/reset-data", json={"password": TEST_PASSWORD})
    assert response.status_code == 400
    with csrf_app.app_context():
        assert Transaction.query.count() == 1


def test_token_de_outra_sessao_e_invalido(csrf_app, csrf_auth_client, user_id_for):
    other = csrf_app.test_client()
    with other.session_transaction() as session:
        session["_user_id"] = str(user_id_for)
        session["_fresh"] = True
    foreign_token = _meta_token(other)
    response = csrf_auth_client.post(
        "/api/transactions/", json=PAYLOAD, headers={"X-CSRFToken": foreign_token}
    )
    assert response.status_code == 400


def test_requisicoes_de_leitura_nao_exigem_token(csrf_auth_client):
    assert csrf_auth_client.get("/api/transactions/?period=all").status_code == 200
    assert csrf_auth_client.get("/api/summary/?period=all").status_code == 200


# --- Regressão estrutural -----------------------------------------------------

def test_todo_formulario_post_dos_templates_tem_token_csrf():
    """Falha se alguém criar um <form method="post"> novo sem o token."""
    checked = 0
    for template in sorted(TEMPLATES.rglob("*.html")):
        for form in FORM_RE.findall(template.read_text(encoding="utf-8")):
            opening_tag = form.split(">", 1)[0]
            if re.search(r'method\s*=\s*["\']post["\']', opening_tag, re.IGNORECASE):
                checked += 1
                assert "csrf_token" in form, f"{template.name}: formulário POST sem csrf_token"
    assert checked >= 4  # login + perfil + senha + cópia de segurança


def test_javascript_envia_o_cabecalho_csrf():
    utils = (TEMPLATES.parent / "static" / "js" / "utils.js").read_text(encoding="utf-8")
    assert "X-CSRFToken" in utils and "csrf-token" in utils
