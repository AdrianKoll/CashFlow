"""Verificação de saúde, usada pelo Docker e por balanceadores de carga."""
import sqlalchemy as sa
from flask import Blueprint, jsonify

from .. import db, limiter

bp = Blueprint("health", __name__)


@bp.get("/healthz")
@limiter.exempt
def healthz():
    """200 se a aplicação responde e o banco aceita uma consulta; 503 caso contrário.

    Não exige login e não expõe detalhes do erro.
    """
    try:
        db.session.execute(sa.text("SELECT 1"))
    except Exception:
        db.session.rollback()
        return jsonify({"status": "indisponivel"}), 503
    return jsonify({"status": "ok"})
