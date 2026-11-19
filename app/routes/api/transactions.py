from datetime import datetime

from flask import Blueprint, jsonify
from flask_login import current_user, login_required

from ... import db, validation as v
from ...helpers import filtered_transactions, tx_item
from ...models import AuditLog, Transaction

bp = Blueprint("api_transactions", __name__, url_prefix="/api/transactions")


def _amount(value) -> float:
    try:
        return v.number(value, "Valor", positive=True)
    except v.ValidationError:
        raise v.ValidationError("Valor inválido.") from None


@bp.route("/")
@login_required
def list_transactions():
    movs, period = filtered_transactions(order="desc")
    return jsonify({
        "period": period,
        "transactions": [tx_item(t) for t in movs],
        "total": len(movs),
    })


@bp.route("/", methods=["POST"])
@login_required
def create_transaction():
    data = v.json_object()
    amount = _amount(data.get("amount"))
    tx_kind = v.kind(data.get("kind", "entrada"))
    title = v.text(data.get("title"), "Título", max_length=120, required=True)
    entity = v.text(data.get("entity"), "Entidade", max_length=120)
    method = v.text(data.get("payment_method"), "Forma de pagamento", max_length=80, default="PIX")
    category = v.category_id(data.get("category_id"))

    try:
        created_at = datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.utcnow()
    except (ValueError, KeyError, TypeError):
        created_at = datetime.utcnow()

    tx = Transaction(
        kind=tx_kind,
        title=title,
        entity=entity,
        amount=amount,
        payment_method=method or "PIX",
        category_id=category,
        created_by=current_user,
        created_at=created_at,
    )
    db.session.add(tx)
    db.session.add(AuditLog(action="adicionou transação", details=tx.title, user=current_user))
    db.session.commit()
    return jsonify(tx_item(tx)), 201


@bp.route("/<int:tx_id>", methods=["PATCH"])
@login_required
def update_transaction(tx_id: int):
    tx = db.get_or_404(Transaction, tx_id)
    data = v.json_object()
    # Valida tudo antes de alterar qualquer campo.
    changes = {}
    if "amount" in data:
        changes["amount"] = _amount(data["amount"])
    if "title" in data:
        changes["title"] = v.text(data["title"], "Título", max_length=120, required=True)
    if "entity" in data:
        changes["entity"] = v.text(data["entity"], "Entidade", max_length=120)
    if "payment_method" in data:
        changes["payment_method"] = v.text(
            data["payment_method"], "Forma de pagamento", max_length=80, default="PIX") or "PIX"
    if "category_id" in data:
        changes["category_id"] = v.category_id(data["category_id"])
    if "kind" in data:
        changes["kind"] = v.kind(data["kind"])
    if "created_at" in data:
        try:
            changes["created_at"] = datetime.fromisoformat(data["created_at"])
        except (ValueError, TypeError):
            pass
    for field, value in changes.items():
        setattr(tx, field, value)
    db.session.add(AuditLog(action="editou transação", details=tx.title, user=current_user))
    db.session.commit()
    return jsonify(tx_item(tx))


@bp.route("/<int:tx_id>", methods=["DELETE"])
@login_required
def delete_transaction(tx_id: int):
    tx = db.get_or_404(Transaction, tx_id)
    title = tx.title
    db.session.delete(tx)
    db.session.add(AuditLog(action="removeu transação", details=title, user=current_user))
    db.session.commit()
    return jsonify({"success": True})
