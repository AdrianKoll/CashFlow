from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required
from ... import db
from ...models import FixedRecord, FixedRecordItem, AuditLog
from ...helpers import fixed_item, fixed_record_total, safe_float, safe_int

bp = Blueprint("api_fixed_records", __name__, url_prefix="/api/fixed-records")


def _load_items_from_data(record: FixedRecord, items_data: list) -> None:
    for child in list(record.items):
        db.session.delete(child)
    for row in items_data:
        qty = safe_float(row.get("quantity"), 1.0)
        unit_price = safe_float(row.get("unit_price"))
        amount = qty * unit_price
        db.session.add(FixedRecordItem(
            fixed_record=record,
            name=row.get("name", "").strip(),
            quantity=qty,
            unit=row.get("unit", "un"),
            unit_price=unit_price,
            amount=amount,
            notes=row.get("notes", "").strip(),
        ))
    db.session.flush()
    total = sum(float(child.amount or 0) for child in record.items)
    if total > 0:
        record.amount = total


@bp.route("/")
@login_required
def list_fixed_records():
    records = FixedRecord.query.order_by(FixedRecord.id.asc()).all()
    return jsonify([fixed_item(r) for r in records])


@bp.route("/", methods=["POST"])
@login_required
def create_fixed_record():
    data = request.get_json(force=True)
    record = FixedRecord(
        kind=data.get("kind", "saida"),
        title=data.get("title", "").strip(),
        entity=data.get("entity", "").strip(),
        amount=safe_float(data.get("amount")),
        payment_method=data.get("payment_method", "PIX"),
        category_id=data.get("category_id") or None,
        day_of_month=safe_int(data.get("day_of_month"), 1),
        active=bool(data.get("active", True)),
        created_by=current_user,
    )
    db.session.add(record)
    db.session.flush()
    if data.get("items"):
        _load_items_from_data(record, data["items"])
    db.session.add(AuditLog(action="adicionou registro fixo", details=record.title, user=current_user))
    db.session.commit()
    return jsonify(fixed_item(record)), 201


@bp.route("/<int:record_id>", methods=["PATCH"])
@login_required
def update_fixed_record(record_id: int):
    record = FixedRecord.query.get_or_404(record_id)
    data = request.get_json(force=True)
    if "kind" in data:
        record.kind = data["kind"]
    if "title" in data:
        record.title = data["title"].strip()
    if "entity" in data:
        record.entity = data["entity"].strip()
    if "amount" in data:
        record.amount = safe_float(data["amount"])
    if "payment_method" in data:
        record.payment_method = data["payment_method"]
    if "category_id" in data:
        record.category_id = data["category_id"] or None
    if "day_of_month" in data:
        record.day_of_month = safe_int(data["day_of_month"], 1)
    if "active" in data:
        record.active = bool(data["active"])
    if "last_generated_month" in data:
        record.last_generated_month = data["last_generated_month"]
    if "items" in data:
        _load_items_from_data(record, data["items"])
    db.session.add(AuditLog(action="editou registro fixo", details=record.title, user=current_user))
    db.session.commit()
    return jsonify(fixed_item(record))


@bp.route("/<int:record_id>", methods=["DELETE"])
@login_required
def delete_fixed_record(record_id: int):
    record = FixedRecord.query.get_or_404(record_id)
    title = record.title
    db.session.delete(record)
    db.session.add(AuditLog(action="removeu registro fixo", details=title, user=current_user))
    db.session.commit()
    return jsonify({"success": True})


# ---------------------------------------------------------------------------
# Summary dashboard
# ---------------------------------------------------------------------------

@bp.route("/summary")
@login_required
def fixed_records_summary():
    rows = FixedRecord.query.all()
    ativos = [x for x in rows if x.active]
    despesa = sum(fixed_record_total(x) for x in ativos if x.kind == "saida")
    renda = sum(fixed_record_total(x) for x in ativos if x.kind == "entrada")
    itens = sum(len(x.items or []) for x in ativos)
    categorias: dict = {}
    for x in ativos:
        name = x.category.name if x.category else "Fixas"
        categorias[name] = categorias.get(name, 0) + fixed_record_total(x)
    maiores = sorted([fixed_item(x) for x in ativos], key=lambda x: x["amount"], reverse=True)[:5]
    return jsonify({
        "records_total": len(rows),
        "active_total": len(ativos),
        "inactive_total": len(rows) - len(ativos),
        "monthly_expense": despesa,
        "monthly_income": renda,
        "balance": renda - despesa,
        "items_total": itens,
        "categories": [
            {"label": k, "amount": v}
            for k, v in sorted(categorias.items(), key=lambda kv: kv[1], reverse=True)
        ],
        "top_records": maiores,
    })


# ---------------------------------------------------------------------------
# Geração manual de despesas recorrentes do mês
# ---------------------------------------------------------------------------

@bp.route("/generate-now", methods=["POST"])
@login_required
def generate_fixed_now():
    from ...database import generate_due_fixed_records
    generated = generate_due_fixed_records()
    return jsonify({"ok": True, "generated": generated})


# ---------------------------------------------------------------------------
# Sub-recurso: itens de um registro fixo
# ---------------------------------------------------------------------------

@bp.route("/<int:record_id>/items", methods=["GET"])
@login_required
def list_fixed_items(record_id: int):
    record = FixedRecord.query.get_or_404(record_id)
    items = sorted(record.items, key=lambda x: x.id or 0)
    return jsonify([{
        "id": i.id,
        "name": i.name,
        "quantity": i.quantity,
        "unit": i.unit,
        "unit_price": i.unit_price,
        "amount": i.amount,
        "notes": i.notes or "",
    } for i in items])
