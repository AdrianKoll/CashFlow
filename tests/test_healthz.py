"""Endpoint /healthz."""
from app import db


def test_healthz_responde_ok_sem_login(client):
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_healthz_retorna_503_quando_o_banco_falha(app, client, monkeypatch):
    def broken_execute(*args, **kwargs):
        raise RuntimeError("banco fora do ar")

    monkeypatch.setattr(db.session, "execute", broken_execute)
    response = client.get("/healthz")
    assert response.status_code == 503
    assert response.get_json() == {"status": "indisponivel"}
    assert "banco fora do ar" not in response.get_data(as_text=True)
