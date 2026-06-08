from flask import Blueprint, jsonify, request
from flask_login import login_required
from ...helpers import transactions_for_period, build_chart, fmt_brl, period_label, tx_item
from ...helpers import filtered_transactions

bp = Blueprint("api_summary", __name__, url_prefix="/api/summary")


@bp.route("/")
@login_required
def get_summary():
    movs, period = filtered_transactions(order="asc")
    entradas = sum(t.amount for t in movs if t.kind == "entrada")
    saidas = sum(t.amount for t in movs if t.kind == "saida")
    saldo = entradas - saidas

    by_kind = {"Serviços": 0, "Despesas": 0, "Outros": 0}
    for t in movs:
        if t.kind == "entrada":
            by_kind["Serviços"] += t.amount
        elif t.category and t.category.name in ("Fixas", "Materiais"):
            by_kind["Despesas"] += t.amount
        else:
            by_kind["Outros"] += t.amount
    total_dist = sum(by_kind.values()) or 1
    distribution = [
        {"label": k, "value": round(v / total_dist * 100), "amount": v}
        for k, v in by_kind.items()
    ]

    recent = sorted(movs, key=lambda t: t.created_at, reverse=True)[:8]

    chart = build_chart(movs, period)
    return jsonify({
        "period": period,
        "period_label": period_label(period),
        "cards": {
            "entradas": entradas,
            "saidas": saidas,
            "saldo": saldo,
            "saldo_mes": saldo,
        },
        "entradas": entradas,
        "saidas": saidas,
        "saldo": saldo,
        "total_count": len(movs),
        "entradas_fmt": fmt_brl(entradas),
        "saidas_fmt": fmt_brl(saidas),
        "saldo_fmt": fmt_brl(saldo),
        "chart": chart,
        "recent": [tx_item(t) for t in recent],
        "distribution": distribution,
    })
