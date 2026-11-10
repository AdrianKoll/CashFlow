"""Cópias de segurança e reset de dados."""
from pathlib import Path

from app.models import AuditLog, Transaction
from tests.conftest import TEST_PASSWORD


def _add_transactions(client, count=3):
    for index in range(count):
        client.post(
            "/api/transactions/",
            json={"kind": "entrada", "title": f"Venda {index}", "amount": 10 + index},
        )


def test_cria_copia_de_seguranca(app, auth_client):
    response = auth_client.post("/copia/criar", follow_redirects=True)
    assert "Cópia criada:" in response.get_data(as_text=True)
    copias = list((Path(app.instance_path) / "copias").glob("*.sqlite3"))
    assert len(copias) == 1
    with app.app_context():
        assert AuditLog.query.filter_by(action="criou copia").count() == 1


def test_baixa_a_ultima_copia(auth_client):
    auth_client.post("/copia/criar")
    response = auth_client.get("/copia/baixar")
    assert response.status_code == 200
    assert "attachment" in response.headers["Content-Disposition"]
    assert response.data.startswith(b"SQLite format 3")


def test_baixar_sem_nenhuma_copia_avisa_e_redireciona(auth_client):
    response = auth_client.get("/copia/baixar", follow_redirects=True)
    assert "Nenhuma cópia encontrada" in response.get_data(as_text=True)


def test_reset_com_senha_errada_e_recusado_e_preserva_dados(app, auth_client):
    _add_transactions(auth_client)
    response = auth_client.post("/api/reset-data", json={"password": "errada"})
    assert response.status_code == 403
    assert response.get_json()["ok"] is False
    with app.app_context():
        assert Transaction.query.count() == 3


def test_reset_sem_senha_e_recusado(app, auth_client):
    _add_transactions(auth_client, count=1)
    assert auth_client.post("/api/reset-data", json={}).status_code == 403
    with app.app_context():
        assert Transaction.query.count() == 1


def test_reset_correto_cria_copia_antes_e_remove_movimentacoes(app, auth_client):
    _add_transactions(auth_client)
    response = auth_client.post("/api/reset-data", json={"password": TEST_PASSWORD})
    body = response.get_json()
    assert response.status_code == 200
    assert body["ok"] is True
    assert body["removed"] == 3
    assert body["copia"] and "antes_reset" in body["copia"]
    with app.app_context():
        assert Transaction.query.count() == 0
        assert AuditLog.query.filter_by(action="resetou dados").count() == 1
