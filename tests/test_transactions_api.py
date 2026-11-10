"""API de movimentações (/api/transactions) e resumo (/api/summary)."""
from app.models import AuditLog, Transaction


def _create(client, **overrides):
    payload = {"kind": "entrada", "title": "Venda", "amount": 150.5, "payment_method": "PIX"}
    payload.update(overrides)
    return client.post("/api/transactions/", json=payload)


def test_lista_vazia_no_inicio(auth_client):
    data = auth_client.get("/api/transactions/?period=all").get_json()
    assert data["total"] == 0
    assert data["transactions"] == []


def test_cria_movimentacao_valida(auth_client):
    response = _create(auth_client)
    assert response.status_code == 201
    body = response.get_json()
    assert body["title"] == "Venda"
    assert body["amount"] == 150.5
    assert body["kind"] == "entrada"
    listed = auth_client.get("/api/transactions/?period=all").get_json()
    assert listed["total"] == 1


def test_rejeita_valor_zero_negativo_ou_invalido(auth_client):
    for amount in (0, -10, "abc", None, ""):
        response = _create(auth_client, amount=amount)
        assert response.status_code == 400, amount
        assert response.get_json() == {"error": "Valor inválido."}
    assert auth_client.get("/api/transactions/?period=all").get_json()["total"] == 0


def test_cria_registra_auditoria_com_usuario(app, auth_client, user_id):
    _create(auth_client, title="Corte de cabelo")
    with app.app_context():
        log = AuditLog.query.filter_by(action="adicionou transação").one()
        assert log.details == "Corte de cabelo"
        assert log.user_id == user_id


def test_edita_movimentacao(auth_client):
    tx_id = _create(auth_client).get_json()["id"]
    response = auth_client.patch(
        f"/api/transactions/{tx_id}", json={"amount": 200, "title": "Venda editada"}
    )
    assert response.status_code == 200
    assert response.get_json()["amount"] == 200.0
    assert response.get_json()["title"] == "Venda editada"


def test_remove_movimentacao_e_depois_retorna_404(app, auth_client):
    tx_id = _create(auth_client).get_json()["id"]
    assert auth_client.delete(f"/api/transactions/{tx_id}").get_json() == {"success": True}
    with app.app_context():
        assert Transaction.query.count() == 0
    assert auth_client.patch(f"/api/transactions/{tx_id}", json={"amount": 1}).status_code == 404
    assert auth_client.delete(f"/api/transactions/{tx_id}").status_code == 404


def test_resumo_calcula_entradas_saidas_e_saldo(auth_client):
    _create(auth_client, kind="entrada", amount=100)
    _create(auth_client, kind="entrada", title="Outra venda", amount=50)
    _create(auth_client, kind="saida", title="Material", amount=40)
    summary = auth_client.get("/api/summary/?period=all").get_json()
    assert summary["entradas"] == 150
    assert summary["saidas"] == 40
    assert summary["saldo"] == 110
    assert summary["total_count"] == 3
    assert summary["saldo_fmt"] == "R$ 110,00"


def test_filtro_de_periodo_hoje_inclui_movimentacao_recente(auth_client):
    _create(auth_client)
    assert auth_client.get("/api/transactions/?period=today").get_json()["total"] == 1
    assert auth_client.get("/api/transactions/?period=year").get_json()["total"] == 1


def test_filtro_de_periodo_exclui_movimentacao_antiga(auth_client):
    _create(auth_client, created_at="2020-01-15T10:00:00")
    assert auth_client.get("/api/transactions/?period=today").get_json()["total"] == 0
    assert auth_client.get("/api/transactions/?period=all").get_json()["total"] == 1
