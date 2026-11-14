from flask import Blueprint, redirect, url_for, flash, send_file, jsonify, request
from flask_login import current_user, login_required
from werkzeug.security import check_password_hash
from .. import db
from ..models import Transaction, AuditLog
from ..database import (
    BackupError,
    create_database_copia,
    generate_due_fixed_records,
    latest_copia_path,
)

bp = Blueprint("backup", __name__)


@bp.before_app_request
def run_monthly_fixed_records():
    try:
        if current_user.is_authenticated:
            generate_due_fixed_records()
    except Exception:
        # No PostgreSQL, um erro deixa a transação abortada: sem o rollback, as
        # consultas seguintes da mesma requisição também falhariam.
        db.session.rollback()


@bp.route("/api/reset-data", methods=["POST"])
@login_required
def reset_data():
    data = request.get_json(silent=True) or {}
    password = data.get("password", "")
    if not check_password_hash(current_user.password_hash, password):
        return jsonify({"ok": False, "error": "Senha incorreta. Reset cancelado."}), 403
    try:
        copia = create_database_copia("antes_reset")
    except BackupError:
        copia = None
    if not copia:
        # Nunca apaga dados sem antes ter uma cópia de segurança.
        return jsonify({
            "ok": False,
            "error": "Não foi possível criar a cópia de segurança. Reset cancelado.",
        }), 500
    total = Transaction.query.count()
    Transaction.query.delete()
    db.session.add(AuditLog(
        action="resetou dados",
        details=f"{total} movimentacoes removidas. Copia: {copia.name}",
        user=current_user,
    ))
    db.session.commit()
    return jsonify({"ok": True, "removed": total, "copia": copia.name})


@bp.route("/copia/criar", methods=["POST"])
@login_required
def create_copia_route():
    try:
        copia = create_database_copia("manual")
    except BackupError:
        copia = None
    if not copia:
        flash("Não foi possível criar a cópia de segurança.", "error")
    else:
        db.session.add(AuditLog(action="criou copia", details=copia.name, user=current_user))
        db.session.commit()
        flash(f"Cópia criada: {copia.name}", "success")
    return redirect(url_for("pages.configuracoes"))


@bp.route("/copia/baixar")
@login_required
def download_latest_copia():
    copia = latest_copia_path()
    if not copia:
        flash("Nenhuma cópia encontrada ainda.", "error")
        return redirect(url_for("pages.configuracoes"))
    return send_file(copia, as_attachment=True, download_name=copia.name, mimetype="application/octet-stream")
