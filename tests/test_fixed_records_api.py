"""Registros fixos (despesas/receitas recorrentes) e geração mensal."""
from app.models import Transaction

RENT = {
    "kind": "saida",
    "title": "Aluguel",
    "day_of_month": 5,
    "items": [
        {"name": "Aluguel da sala", "quantity": 1, "unit_price": 1200},
        {"name": "Condomínio", "quantity": 2, "unit_price": 150},
    ],
}


def _create(client, **overrides):
    payload = {**RENT, **overrides}
    return client.post("/api/fixed-records/", json=payload)


def test_cria_registro_e_calcula_total_pelos_itens(auth_client):
    response = _create(auth_client)
    assert response.status_code == 201
    body = response.get_json()
    assert body["amount"] == 1500.0  # 1200 + 2 x 150
    assert body["items_count"] == 2
    assert body["day_of_month"] == 5


def test_resumo_de_registros_fixos(auth_client):
    _create(auth_client)
    _create(auth_client, kind="entrada", title="Mensalidade", items=[
        {"name": "Plano", "quantity": 1, "unit_price": 500}
    ])
    summary = auth_client.get("/api/fixed-records/summary").get_json()
    assert summary["records_total"] == 2
    assert summary["monthly_expense"] == 1500.0
    assert summary["monthly_income"] == 500.0
    assert summary["balance"] == -1000.0


def test_registro_inativo_nao_entra_no_resumo(auth_client):
    record_id = _create(auth_client).get_json()["id"]
    auth_client.patch(f"/api/fixed-records/{record_id}", json={"active": False})
    summary = auth_client.get("/api/fixed-records/summary").get_json()
    assert summary["active_total"] == 0
    assert summary["inactive_total"] == 1
    assert summary["monthly_expense"] == 0


def test_edita_itens_substitui_os_antigos(auth_client):
    record_id = _create(auth_client).get_json()["id"]
    body = auth_client.patch(
        f"/api/fixed-records/{record_id}",
        json={"items": [{"name": "Só um", "quantity": 1, "unit_price": 10}]},
    ).get_json()
    assert body["items_count"] == 1
    assert body["amount"] == 10.0
    items = auth_client.get(f"/api/fixed-records/{record_id}/items").get_json()
    assert [i["name"] for i in items] == ["Só um"]


def test_remove_registro_e_seus_itens(auth_client):
    record_id = _create(auth_client).get_json()["id"]
    assert auth_client.delete(f"/api/fixed-records/{record_id}").get_json() == {"success": True}
    assert auth_client.get("/api/fixed-records/").get_json() == []
    assert auth_client.get(f"/api/fixed-records/{record_id}/items").status_code == 404


def test_geracao_mensal_cria_uma_unica_transacao_por_mes(app, auth_client):
    _create(auth_client)
    # A primeira requisição autenticada já dispara a geração do mês.
    auth_client.post("/api/fixed-records/generate-now")
    auth_client.post("/api/fixed-records/generate-now")
    auth_client.get("/api/summary/?period=all")
    with app.app_context():
        transactions = Transaction.query.all()
        assert len(transactions) == 1
        assert transactions[0].kind == "saida"
        assert transactions[0].amount == 1500.0
        assert transactions[0].title == "Aluguel"


def test_registro_sem_valor_nao_gera_transacao(app, auth_client):
    auth_client.post("/api/fixed-records/", json={"title": "Vazio", "amount": 0})
    auth_client.post("/api/fixed-records/generate-now")
    with app.app_context():
        assert Transaction.query.count() == 0
