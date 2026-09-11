from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required
from ... import db
from ...models import Product, AuditLog
from ...helpers import product_item, safe_float, safe_int

bp = Blueprint("api_products", __name__, url_prefix="/api/products")


@bp.route("/")
@login_required
def list_products():
    show_all = request.args.get("all", "0") == "1"
    q = Product.query if show_all else Product.query.filter_by(active=True)
    products = q.order_by(Product.name.asc()).all()
    return jsonify([product_item(p) for p in products])


@bp.route("/", methods=["POST"])
@login_required
def create_product():
    data = request.get_json(force=True)
    p = Product(
        name=data.get("name", "").strip(),
        unit=data.get("unit", "un"),
        unit_price=safe_float(data.get("unit_price")),
        default_quantity=safe_float(data.get("default_quantity"), 1.0),
        notes=data.get("notes", "").strip(),
        active=bool(data.get("active", True)),
    )
    db.session.add(p)
    db.session.add(AuditLog(action="adicionou produto", details=p.name, user=current_user))
    db.session.commit()
    return jsonify(product_item(p)), 201


@bp.route("/<int:product_id>", methods=["PATCH"])
@login_required
def update_product(product_id: int):
    p = Product.query.get_or_404(product_id)
    data = request.get_json(force=True)
    if "name" in data:
        p.name = data["name"].strip()
    if "unit" in data:
        p.unit = data["unit"]
    if "unit_price" in data:
        p.unit_price = safe_float(data["unit_price"])
    if "default_quantity" in data:
        p.default_quantity = safe_float(data["default_quantity"], 1.0)
    if "notes" in data:
        p.notes = data["notes"].strip()
    if "active" in data:
        p.active = bool(data["active"])
    db.session.add(AuditLog(action="editou produto", details=p.name, user=current_user))
    db.session.commit()
    return jsonify(product_item(p))


@bp.route("/<int:product_id>", methods=["DELETE"])
@login_required
def delete_product(product_id: int):
    p = Product.query.get_or_404(product_id)
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
