from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required
from ... import db, validation as v
from ...models import Product, AuditLog
from ...helpers import product_item

bp = Blueprint("api_products", __name__, url_prefix="/api/products")


@bp.route("/")
@login_required
def list_products():
    show_all = request.args.get("all", "0") == "1"
    q = Product.query if show_all else Product.query.filter_by(active=True)
    products = q.order_by(Product.name.asc()).all()
    return jsonify([product_item(p) for p in products])


def _fields(data: dict, *, full: bool) -> dict:
    """Valida os campos presentes (todos, na criação) e devolve os valores limpos."""
    out = {}
    if full or "name" in data:
        out["name"] = v.text(data.get("name"), "Nome", max_length=120, required=True)
    if full or "unit" in data:
        out["unit"] = v.text(data.get("unit"), "Unidade", max_length=30, default="un") or "un"
    if full or "unit_price" in data:
        out["unit_price"] = v.number(data.get("unit_price"), "Preço", default=0.0)
    if full or "default_quantity" in data:
        out["default_quantity"] = v.number(
            data.get("default_quantity"), "Quantidade", maximum=v.MAX_QUANTITY, default=1.0)
    if full or "notes" in data:
        out["notes"] = v.text(data.get("notes"), "Observações", max_length=180)
    if "active" in data or full:
        out["active"] = bool(data.get("active", True))
    return out


@bp.route("/", methods=["POST"])
@login_required
def create_product():
    p = Product(**_fields(v.json_object(), full=True))
    db.session.add(p)
    db.session.add(AuditLog(action="adicionou produto", details=p.name, user=current_user))
    db.session.commit()
    return jsonify(product_item(p)), 201


@bp.route("/<int:product_id>", methods=["PATCH"])
@login_required
def update_product(product_id: int):
    p = db.get_or_404(Product, product_id)
    for field, value in _fields(v.json_object(), full=False).items():
        setattr(p, field, value)
    db.session.add(AuditLog(action="editou produto", details=p.name, user=current_user))
    db.session.commit()
    return jsonify(product_item(p))


@bp.route("/<int:product_id>", methods=["DELETE"])
@login_required
def delete_product(product_id: int):
    p = db.get_or_404(Product, product_id)
    name = p.name
    db.session.delete(p)
    db.session.add(AuditLog(action="removeu produto", details=name, user=current_user))
    db.session.commit()
    return jsonify({"success": True})


@bp.route("/categories")
@login_required
def list_categories():
    from ...models import Category
    return jsonify([
        {"id": c.id, "name": c.name, "color": c.color, "icon": c.icon}
        for c in Category.query.order_by(Category.name.asc()).all()
    ])
