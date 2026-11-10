"""Limite de tentativas no login (por usuário e por IP)."""
import pytest

from app import limiter
from tests.conftest import TEST_PASSWORD, TEST_USERNAME, create_test_user, make_app

BLOCKED_MESSAGE = "Muitas tentativas. Aguarde alguns minutos e tente novamente."


@pytest.fixture()
def limited_app(tmp_path):
    app = make_app(tmp_path, RATELIMIT_ENABLED=True)
    limiter.reset()
    create_test_user(app)
    return app


def _login(client, username=TEST_USERNAME, password=TEST_PASSWORD, **kwargs):
    return client.post("/login", data={"username": username, "password": password}, **kwargs)


def test_bloqueia_apos_5_falhas_para_o_mesmo_usuario(limited_app):
    client = limited_app.test_client()
    for attempt in range(5):
        # Maiúsculas/minúsculas contam como o mesmo usuário.
        username = TEST_USERNAME.upper() if attempt % 2 else TEST_USERNAME
        assert _login(client, username, "errada").status_code == 200

    response = _login(client, TEST_USERNAME, "errada")
    assert response.status_code == 429
    assert BLOCKED_MESSAGE in response.get_data(as_text=True)
    assert int(response.headers["Retry-After"]) > 0


def test_senha_correta_tambem_e_bloqueada_durante_o_bloqueio(limited_app):
    client = limited_app.test_client()
    for _ in range(5):
        _login(client, password="errada")
    assert _login(client).status_code == 429  # a senha certa não fura o limite


def test_login_correto_nao_consome_o_limite(limited_app):
    for _ in range(12):  # acima dos dois limites (5 por usuário e 10 por IP)
        assert _login(limited_app.test_client()).status_code == 302


def test_poucas_falhas_antes_do_acerto_nao_bloqueiam_o_usuario_legitimo(limited_app):
    client = limited_app.test_client()
    for _ in range(3):
        assert _login(client, password="errada").status_code == 200
    assert _login(client).status_code == 302


def test_bloqueio_de_um_usuario_nao_afeta_outro_usuario(limited_app):
    create_test_user(limited_app, username="outro", password="outra-senha-123")
    client = limited_app.test_client()
    for _ in range(5):
        _login(client, password="errada")
    assert _login(client).status_code == 429
    assert _login(limited_app.test_client(), "outro", "outra-senha-123").status_code == 302


def test_limite_por_ip_com_usuarios_diferentes(limited_app):
    client = limited_app.test_client()
    for index in range(10):
        assert _login(client, f"alvo{index}", "errada").status_code == 200
    assert _login(client, "alvo-novo", "errada").status_code == 429


def test_get_da_pagina_de_login_nao_e_limitado(limited_app):
    client = limited_app.test_client()
    assert all(client.get("/login").status_code == 200 for _ in range(30))


def test_rotas_autenticadas_nao_sao_afetadas_pelo_bloqueio(limited_app):
    client = limited_app.test_client()
    for index in range(10):
        _login(client, f"alvo{index}", "errada")
    assert _login(client, "alvo-novo", "errada").status_code == 429

    with client.session_transaction() as session:
        session["_user_id"] = "1"
        session["_fresh"] = True
    assert client.get("/").status_code == 200


def test_x_forwarded_for_e_ignorado_por_padrao(limited_app):
    """Sem proxy confiável, forjar o cabeçalho não permite fugir do limite."""
    client = limited_app.test_client()
    for index in range(10):
        response = client.post(
            "/login",
            data={"username": f"alvo{index}", "password": "errada"},
            headers={"X-Forwarded-For": f"10.0.0.{index}"},
        )
        assert response.status_code == 200
    response = client.post(
        "/login",
        data={"username": "alvo-novo", "password": "errada"},
        headers={"X-Forwarded-For": "203.0.113.99"},
    )
    assert response.status_code == 429


def test_x_forwarded_for_e_usado_quando_ha_proxy_confiavel(tmp_path):
    app = make_app(tmp_path, RATELIMIT_ENABLED=True, TRUSTED_PROXIES=1)
    limiter.reset()
    create_test_user(app)
    client = app.test_client()
    proxy_ip = {"X-Forwarded-For": "198.51.100.7"}

    for index in range(10):
        client.post("/login", data={"username": f"alvo{index}", "password": "errada"},
                    headers=proxy_ip)
    blocked = client.post("/login", data={"username": "x", "password": "errada"},
                          headers=proxy_ip)
    assert blocked.status_code == 429

    # Outro cliente real (outro IP atrás do mesmo proxy) segue liberado.
    other = client.post(
        "/login",
        data={"username": TEST_USERNAME, "password": TEST_PASSWORD},
        headers={"X-Forwarded-For": "198.51.100.8"},
    )
    assert other.status_code == 302
