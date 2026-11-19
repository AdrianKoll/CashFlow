"""Validação de entrada e endurecimento: dados inválidos nunca viram erro 500
nem corrompem o que já está salvo."""
import threading
from datetime import datetime

import pytest

from app import db
from app.database import generate_due_fixed_records
from app.models import FixedRecord, Transaction
from tests.conftest import create_test_user

VALID_TX = {"kind": "entrada", "title": "Venda", "amount": 10}


def _post_tx(client, **override):
    return client.post("/api/transactions/", json={**VALID_TX, **override})


# --- Movimentações ---------------------------------------------------------------

@pytest.mark.parametrize("amount", ["nan", "NaN", "inf", "-inf", "Infinity", 1e400, 1e15])
def test_valor_nao_finito_ou_gigante_e_recusado(auth_client, amount):
    response = _post_tx(auth_client, amount=amount)
    assert response.status_code == 400


def test_dashboard_continua_funcionando_depois_de_tentar_envenenar_dados(auth_client):
    _post_tx(auth_client, amount="nan")
    _post_tx(auth_client, kind="outro")
    assert auth_client.get("/api/summary/?period=year").status_code == 200


@pytest.mark.parametrize("kind", ["outro", "", None, 5, "ENTRADA"])
def test_tipo_invalido_e_recusado(auth_client, kind):
    assert _post_tx(auth_client, kind=kind).status_code == 400


def test_titulo_vazio_ou_so_espacos_e_recusado(auth_client):
    assert _post_tx(auth_client, title="   ").status_code == 400


@pytest.mark.parametrize("field,limit", [("title", 120), ("entity", 120), ("payment_method", 80)])
def test_texto_acima_do_limite_da_coluna_e_recusado_sem_erro_500(auth_client, field, limit):
    assert _post_tx(auth_client, **{field: "x" * (limit + 1)}).status_code == 400
    assert _post_tx(auth_client, **{field: "x" * limit}).status_code == 201


def test_categoria_inexistente_e_recusada(auth_client):
    assert _post_tx(auth_client, category_id=99999).status_code == 400


def test_corpo_json_que_nao_e_objeto_e_recusado(auth_client):
    for body in ([1, 2], "texto", 5, None):
        assert auth_client.post("/api/transactions/", json=body).status_code == 400


def test_corpo_que_nao_e_json_e_recusado(auth_client):
    response = auth_client.post("/api/transactions/", data="não é json",
                                content_type="application/json")
    assert response.status_code == 400


def test_corpo_gigante_e_recusado(auth_client):
    response = auth_client.post("/api/transactions/", json={**VALID_TX, "title": "x" * 3_000_000})
    assert response.status_code == 413


def test_edicao_nao_aceita_valor_zero_negativo_nem_nan(auth_client):
    tx_id = _post_tx(auth_client).get_json()["id"]
    for amount in (0, -5, "nan"):
        assert auth_client.patch(f"/api/transactions/{tx_id}", json={"amount": amount}).status_code == 400
    assert auth_client.patch(f"/api/transactions/{tx_id}", json={"kind": "xyz"}).status_code == 400
    assert auth_client.patch(f"/api/transactions/{tx_id}", json={"title": "y" * 500}).status_code == 400
    assert auth_client.patch(f"/api/transactions/{tx_id}", json={"category_id": 99999}).status_code == 400
    assert auth_client.get("/api/transactions/?period=year").get_json()["transactions"][0]["amount"] == 10


# --- Produtos ----------------------------------------------------------------------

def test_produto_invalido_e_recusado(auth_client):
    post = lambda **d: auth_client.post("/api/products/", json={"name": "Café", **d})
    assert post().status_code == 201
    assert auth_client.post("/api/products/", json={"name": " "}).status_code == 400
    assert post(name="n" * 121).status_code == 400
    assert post(unit="u" * 31).status_code == 400
    assert post(notes="n" * 181).status_code == 400
    assert post(unit_price="nan").status_code == 400
    assert post(unit_price=-1).status_code == 400
    assert post(default_quantity="inf").status_code == 400


# --- Registros fixos -----------------------------------------------------------------

def test_registro_fixo_invalido_e_recusado(auth_client):
    post = lambda **d: auth_client.post("/api/fixed-records/", json={"title": "Aluguel", **d})
    assert post(items=[{"name": "a", "quantity": 1, "unit_price": 10}]).status_code == 201
    assert post(kind="x").status_code == 400
    assert post(title="t" * 121).status_code == 400
    assert post(day_of_month=0).status_code == 400
    assert post(day_of_month=32).status_code == 400
    assert post(amount="nan").status_code == 400
    assert post(items="não é lista").status_code == 400
    assert post(items=[{"name": "a", "quantity": "nan", "unit_price": 1}]).status_code == 400
    assert post(items=[{"name": "a", "quantity": 1, "unit_price": -3}]).status_code == 400
    assert post(items=[{"name": "n" * 121}]).status_code == 400
    assert post(items=[{"name": "a", "unit_price": 1}] * 201).status_code == 400


def test_mes_gerado_so_aceita_formato_ano_mes(auth_client):
    record_id = auth_client.post("/api/fixed-records/", json={"title": "Luz"}).get_json()["id"]
    patch = lambda value: auth_client.patch(
        f"/api/fixed-records/{record_id}", json={"last_generated_month": value})
    assert patch("2026-11").status_code == 200
    assert patch("2026-13").status_code == 400
    assert patch("x" * 50).status_code == 400
    assert patch("").status_code == 200


# --- Perfil e senha ---------------------------------------------------------------------

def test_perfil_com_nome_ou_usuario_gigante_e_recusado_sem_erro_500(auth_client):
    from tests.conftest import TEST_PASSWORD
    for name, username in (("n" * 91, "ok"), ("ok", "u" * 61)):
        response = auth_client.post(
            "/configuracoes/perfil",
            data={"name": name, "username": username, "password": TEST_PASSWORD},
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert "no máximo" in response.get_data(as_text=True)


def test_nova_senha_exige_12_caracteres(auth_client):
    from tests.conftest import TEST_PASSWORD
    response = auth_client.post(
        "/configuracoes/senha",
        data={"current_password": TEST_PASSWORD, "new_password": "curta12345",
              "confirm_password": "curta12345"},
        follow_redirects=True,
    )
    assert "pelo menos 12 caracteres" in response.get_data(as_text=True)


# --- Relatório PDF ------------------------------------------------------------------------

@pytest.mark.parametrize("title", [
    '<img src="/etc/passwd" width="10" height="10"/>',
    '<img src="http://127.0.0.1:1/x.png"/>',
    "<b>sem fechar",
    '<a href="javascript:alert(1)">x</a>',
    "<font size='abc'>x</font>",
    "A & B < C > D",
])
def test_pdf_trata_titulo_como_texto_puro(auth_client, title):
    assert _post_tx(auth_client, title=title).status_code == 201
    response = auth_client.get("/relatorios/pdf?period=year")
    assert response.status_code == 200
    assert response.data.startswith(b"%PDF")


# --- Cabeçalhos de segurança ------------------------------------------------------------------

def test_cabecalhos_de_seguranca(auth_client):
    for path in ("/", "/login", "/api/summary/", "/healthz"):
        headers = auth_client.get(path).headers
        assert headers["X-Content-Type-Options"] == "nosniff"
        assert headers["X-Frame-Options"] == "DENY"
        assert headers["Referrer-Policy"] == "same-origin"
        csp = headers["Content-Security-Policy"]
        assert "frame-ancestors 'none'" in csp
        assert "default-src 'self'" in csp
        assert "base-uri 'self'" in csp
        assert "object-src 'none'" in csp


def test_hsts_so_com_cookie_seguro(tmp_path):
    from tests.conftest import make_app
    plain = make_app(tmp_path).test_client().get("/login")
    assert "Strict-Transport-Security" not in plain.headers
    secure = make_app(tmp_path, SESSION_COOKIE_SECURE=True).test_client().get("/login")
    assert "max-age=" in secure.headers["Strict-Transport-Security"]


def test_respostas_autenticadas_nao_sao_guardadas_em_cache(auth_client):
    assert "no-store" in auth_client.get("/api/summary/").headers["Cache-Control"]
    assert "no-store" in auth_client.get("/").headers["Cache-Control"]


# --- Logout ----------------------------------------------------------------------------------

def test_logout_por_get_nao_encerra_a_sessao(auth_client):
    assert auth_client.get("/logout").status_code == 405
    assert auth_client.get("/api/summary/").status_code == 200


def test_logout_por_post_encerra_a_sessao(auth_client):
    assert auth_client.post("/logout").status_code == 302
    assert auth_client.get("/api/summary/").status_code in (302, 401)


# --- Login: enumeração de usuários ---------------------------------------------------------------

def test_usuario_inexistente_tambem_gasta_o_calculo_do_hash(client, user_id, monkeypatch):
    import app.routes.auth as auth_module
    calls = []
    real = auth_module.check_password_hash
    monkeypatch.setattr(auth_module, "check_password_hash",
                        lambda h, p: calls.append(h) or real(h, p))
    client.post("/login", data={"username": "nao-existe", "password": "qualquer"})
    assert len(calls) == 1


# --- Geração mensal concorrente ----------------------------------------------------------------------

def test_geracao_mensal_concorrente_nao_duplica_lancamentos(app, user_id):
    with app.app_context():
        db.session.add(FixedRecord(kind="saida", title="Aluguel", amount=100, active=True,
                                   created_by_id=user_id))
        db.session.commit()

    barrier = threading.Barrier(6)
    results, errors = [], []

    def worker():
        try:
            with app.app_context():
                barrier.wait(timeout=10)
                results.append(generate_due_fixed_records())
                db.session.remove()
        except Exception as exc:  # pragma: no cover - só aparece se falhar
            errors.append(exc)

    threads = [threading.Thread(target=worker) for _ in range(6)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)

    assert not errors, errors
    with app.app_context():
        assert Transaction.query.filter_by(title="Aluguel").count() == 1
    assert sum(results) == 1
