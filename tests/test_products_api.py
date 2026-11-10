"""API de produtos reutilizáveis (/api/products)."""


def _create(client, **overrides):
    payload = {"name": "Corte", "unit": "un", "unit_price": 35, "default_quantity": 1}
    payload.update(overrides)
    return client.post("/api/products/", json=payload)


def test_categorias_iniciais_sao_criadas(auth_client):
    names = {c["name"] for c in auth_client.get("/api/products/categories").get_json()}
    assert names == {"Vendas", "Despesas", "Fixas", "Produtos"}


def test_cria_e_lista_produto(auth_client):
    response = _create(auth_client)
    assert response.status_code == 201
    assert response.get_json()["unit_price"] == 35.0
    products = auth_client.get("/api/products/").get_json()
    assert [p["name"] for p in products] == ["Corte"]


def test_produto_inativo_so_aparece_com_all(auth_client):
    product_id = _create(auth_client).get_json()["id"]
    auth_client.patch(f"/api/products/{product_id}", json={"active": False})
    assert auth_client.get("/api/products/").get_json() == []
    assert len(auth_client.get("/api/products/?all=1").get_json()) == 1


def test_edita_preco_e_nome(auth_client):
    product_id = _create(auth_client).get_json()["id"]
    body = auth_client.patch(
        f"/api/products/{product_id}", json={"name": "  Barba  ", "unit_price": 42.5}
    ).get_json()
    assert body["name"] == "Barba"
    assert body["unit_price"] == 42.5


def test_remove_produto(auth_client):
    product_id = _create(auth_client).get_json()["id"]
    assert auth_client.delete(f"/api/products/{product_id}").get_json() == {"success": True}
    assert auth_client.get("/api/products/?all=1").get_json() == []
    assert auth_client.delete(f"/api/products/{product_id}").status_code == 404
