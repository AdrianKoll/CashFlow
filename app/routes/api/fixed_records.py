from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required
from ... import db, validation as v
from ...models import FixedRecord, FixedRecordItem, AuditLog
from ...helpers import fixed_item, fixed_record_total

bp = Blueprint("api_fixed_records", __name__, url_prefix="/api/fixed-records")


def _validated_items(items_data) -> list[dict]:
    if not isinstance(items_data, list):
        raise v.ValidationError("Os itens devem ser uma lista.")
    if len(items_data) > v.MAX_ITEMS_PER_RECORD:
        raise v.ValidationError(f"No máximo {v.MAX_ITEMS_PER_RECORD} itens por registro.")
    rows = []
    for row in items_data:
        if not isinstance(row, dict):
            raise v.ValidationError("Item inválido.")
        quantity = v.number(row.get("quantity"), "Quantidade", maximum=v.MAX_QUANTITY, default=1.0)
        unit_price = v.number(row.get("unit_price"), "Preço do item", default=0.0)
        amount = quantity * unit_price
        if amount > v.MAX_MONEY:
            raise v.ValidationError("Valor do item fora do intervalo permitido.")
        rows.append({
            "name": v.text(row.get("name"), "Nome do item", max_length=120),
            "quantity": quantity,
            "unit": v.text(row.get("unit"), "Unidade", max_length=30, default="un") or "un",
            "unit_price": unit_price,
            "amount": amount,
            "notes": v.text(row.get("notes"), "Observações do item", max_length=160),
        })
    return rows


def _load_items(record: FixedRecord, rows: list[dict]) -> None:
    for child in list(record.items):
        db.session.delete(child)
    for row in rows:
        db.session.add(FixedRecordItem(fixed_record=record, **row))
    db.session.flush()
    total = sum(float(child.amount or 0) for child in record.items)
    if total > 0:
        record.amount = total


def _fields(data: dict, *, full: bool) -> dict:
    out = {}
    if full or "kind" in data:
        out["kind"] = v.kind(data.get("kind", "saida"))
    if full or "title" in data:
        out["title"] = v.text(data.get("title"), "Título", max_length=120, required=True)
    if full or "entity" in data:
        out["entity"] = v.text(data.get("entity"), "Entidade", max_length=120)
    if full or "amount" in data:
        out["amount"] = v.number(data.get("amount"), "Valor", default=0.0)
    if full or "payment_method" in data:
        out["payment_method"] = v.text(
            data.get("payment_method"), "Forma de pagamento", max_length=80, default="PIX") or "PIX"
    if full or "category_id" in data:
        out["category_id"] = v.category_id(data.get("category_id"))
    if full or "day_of_month" in data:
        out["day_of_month"] = v.day_of_month(data.get("day_of_month"))
    if full or "active" in data:
        out["active"] = bool(data.get("active", True))
    if "last_generated_month" in data:
        out["last_generated_month"] = v.month_key(data["last_generated_month"])
    return out


@bp.route("/")
@login_required
def list_fixed_records():
    records = FixedRecord.query.order_by(FixedRecord.id.asc()).all()
    return jsonify([fixed_item(r) for r in records])


@bp.route("/", methods=["POST"])
@login_required
def create_fixed_record():
    data = v.json_object()
    fields = _fields(data, full=True)
    rows = _validated_items(data["items"]) if data.get("items") else []
    record = FixedRecord(created_by=current_user, **fields)
    db.session.add(record)
    db.session.flush()
    if rows:
        _load_items(record, rows)
    db.session.add(AuditLog(action="adicionou registro fixo", details=record.title, user=current_user))
    db.session.commit()
    return jsonify(fixed_item(record)), 201


@bp.route("/<int:record_id>", methods=["PATCH"])
@login_required
def update_fixed_record(record_id: int):
    record = db.get_or_404(FixedRecord, record_id)
    data = v.json_object()
    fields = _fields(data, full=False)
    rows = _validated_items(data["items"]) if "items" in data else None
    for field, value in fields.items():
        setattr(record, field, value)
    if rows is not None:
        _load_items(record, rows)
    db.session.add(AuditLog(action="editou registro fixo", details=record.title, user=current_user))
    db.session.commit()
    return jsonify(fixed_item(record))


@bp.route("/<int:record_id>", methods=["DELETE"])
@login_required
def delete_fixed_record(record_id: int):
    record = db.get_or_404(FixedRecord, record_id)
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
    record = db.get_or_404(FixedRecord, record_id)
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
