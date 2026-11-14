"""Bancos criados antes das colunas de quantidade/unidade continuam funcionando."""
import sqlalchemy as sa

from app.database import ensure_database_columns
from app import db


def test_adiciona_colunas_faltantes_e_preenche_valores(app):
    with app.app_context():
        # Simula o esquema antigo: recria a tabela sem as colunas novas.
        db.session.remove()
        with db.engine.begin() as conn:
            conn.execute(sa.text("DROP TABLE fixed_record_item"))
            conn.execute(sa.text(
                "CREATE TABLE fixed_record_item ("
                "id INTEGER PRIMARY KEY, amount FLOAT)"
            ))
            conn.execute(sa.text("INSERT INTO fixed_record_item (id, amount) VALUES (1, 25.5)"))

        ensure_database_columns()
        ensure_database_columns()  # idempotente

        columns = {c["name"] for c in sa.inspect(db.engine).get_columns("fixed_record_item")}
        assert {"quantity", "unit", "unit_price"} <= columns
        with db.engine.connect() as conn:
            row = conn.execute(sa.text(
                "SELECT quantity, unit, unit_price FROM fixed_record_item WHERE id = 1"
            )).one()
        assert tuple(row) == (1, "un", 25.5)
