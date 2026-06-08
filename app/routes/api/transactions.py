from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required
from datetime import datetime
from ... import db
from ...models import Transaction, AuditLog
from ...helpers import filtered_transactions, tx_item, safe_float

bp = Blueprint("api_transactions", __name__, url_prefix="/api/transactions")


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
    data = request.get_json(force=True)
    amount = safe_float(data.get("amount"))
    if amount <= 0:
        return jsonify({"error": "Valor inválido."}), 400

    try:
        created_at = datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.utcnow()
    except (ValueError, KeyError):
        created_at = datetime.utcnow()

    tx = Transaction(
        kind=data.get("kind", "entrada"),
        title=data.get("title", "").strip(),
        entity=data.get("entity", "").strip(),
        amount=amount,
        payment_method=data.get("payment_method", "PIX"),
        category_id=data.get("category_id") or None,
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
    tx = Transaction.query.get_or_404(tx_id)
    data = request.get_json(force=True)
    if "amount" in data:
        tx.amount = safe_float(data["amount"])
    if "title" in data:
        tx.title = data["title"]
    if "entity" in data:
        tx.entity = data["entity"]
    if "payment_method" in data:
        tx.payment_method = data["payment_method"]
    if "category_id" in data:
        tx.category_id = data["category_id"] or None
    if "kind" in data:
        tx.kind = data["kind"]
    if "created_at" in data:
        try:
            tx.created_at = datetime.fromisoformat(data["created_at"])
        except ValueError:
            pass
    db.session.add(AuditLog(action="editou transação", details=tx.title, user=current_user))
    db.session.commit()
    return jsonify(tx_item(tx))


@bp.route("/<int:tx_id>", methods=["DELETE"])
@login_required
def delete_transaction(tx_id: int):
    tx = Transaction.query.get_or_404(tx_id)
    title = tx.title
    db.session.delete(tx)
    db.session.add(AuditLog(action="removeu transação", details=title, user=current_user))
    db.session.commit()
    return jsonify({"success": True})
