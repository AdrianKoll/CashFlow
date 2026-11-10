"""Páginas HTML e relatório em PDF."""
import pytest

PAGES = [
    "/",
    "/movimentacoes",
    "/relatorios",
    "/registros-fixos",
    "/registros-fixos/produtos",
    "/registros-fixos/despesa-mensal",
    "/registros-fixos/gerenciar",
    "/configuracoes",
    "/sobre",
]


@pytest.mark.parametrize("path", PAGES)
def test_paginas_abrem_para_usuario_autenticado(auth_client, path):
    response = auth_client.get(path)
    assert response.status_code == 200
    assert "text/html" in response.content_type


def test_relatorio_pdf_e_gerado(auth_client):
    auth_client.post(
        "/api/transactions/", json={"kind": "entrada", "title": "Venda", "amount": 99.9}
    )
    response = auth_client.get("/relatorios/pdf?period=month")
    assert response.status_code == 200
    assert response.mimetype == "application/pdf"
    assert response.data.startswith(b"%PDF")
    assert "attachment" in response.headers["Content-Disposition"]


def test_relatorio_pdf_funciona_sem_movimentacoes(auth_client):
    response = auth_client.get("/relatorios/pdf?period=today")
    assert response.status_code == 200
    assert response.data.startswith(b"%PDF")
