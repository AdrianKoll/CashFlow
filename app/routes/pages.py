from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file
from flask_login import current_user, login_required
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime
from .. import db
from ..models import AuditLog
from ..database import latest_copia_path
from ..pdf import build_pdf_report
from ..helpers import period_label

bp = Blueprint("pages", __name__)


@bp.route("/")
@login_required
def dashboard():
    return render_template("dashboard.html", user=current_user)


@bp.route("/movimentacoes")
@login_required
def movimentacoes():
    return render_template("movimentacoes.html", user=current_user)


@bp.route("/relatorios")
@login_required
def relatorios():
    return render_template("relatorios.html", user=current_user)


@bp.route("/registros-fixos")
@login_required
def registros_fixos():
    return render_template("registros_fixos/dashboard.html", user=current_user)


@bp.route("/registros-fixos/produtos")
@login_required
def produtos_fixos():
    return render_template("registros_fixos/produtos.html", user=current_user)


@bp.route("/registros-fixos/despesa-mensal")
@login_required
def despesa_mensal():
    return render_template("registros_fixos/despesa_mensal.html", user=current_user)


@bp.route("/registros-fixos/gerenciar")
@login_required
def gerenciar_registros_fixos():
    return render_template("registros_fixos/gerenciar.html", user=current_user)


@bp.route("/configuracoes")
@login_required
def configuracoes():
    latest = latest_copia_path()
    return render_template(
        "configuracoes.html",
        user=current_user,
        latest_copia=latest.name if latest else None,
    )


@bp.route("/sobre")
@login_required
def sobre():
    return render_template("sobre.html", user=current_user)


# ---------------------------------------------------------------------------
# Ações de configuração (POST)
# ---------------------------------------------------------------------------

@bp.route("/configuracoes/perfil", methods=["POST"])
@login_required
def update_profile():
    name = request.form.get("name", "").strip()
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    if not check_password_hash(current_user.password_hash, password):
        flash("Senha atual incorreta. Nenhuma alteração foi salva.", "error")
        return redirect(url_for("pages.configuracoes"))
    if not name or not username:
        flash("Nome e usuário são obrigatórios.", "error")
        return redirect(url_for("pages.configuracoes"))
    if len(name) > 90 or len(username) > 60:
        flash("O nome deve ter no máximo 90 caracteres e o usuário no máximo 60.", "error")
        return redirect(url_for("pages.configuracoes"))
    from ..models import User
    exists = User.query.filter(User.username == username, User.id != current_user.id).first()
    if exists:
        flash("Esse nome de usuário já está em uso.", "error")
        return redirect(url_for("pages.configuracoes"))
    current_user.name = name
    current_user.username = username
    db.session.add(AuditLog(action="atualizou perfil", details="Nome/usuário alterados", user=current_user))
    db.session.commit()
    flash("Perfil atualizado com sucesso.", "success")
    return redirect(url_for("pages.configuracoes"))


@bp.route("/configuracoes/senha", methods=["POST"])
@login_required
def change_password():
    current_password = request.form.get("current_password", "")
    new_password = request.form.get("new_password", "")
    confirm_password = request.form.get("confirm_password", "")
    if not check_password_hash(current_user.password_hash, current_password):
        flash("Senha atual incorreta.", "error")
        return redirect(url_for("pages.configuracoes"))
    if len(new_password) < 12:
        flash("A nova senha precisa ter pelo menos 12 caracteres.", "error")
        return redirect(url_for("pages.configuracoes"))
    if len(new_password) > 128:
        flash("A nova senha pode ter no máximo 128 caracteres.", "error")
        return redirect(url_for("pages.configuracoes"))
    if new_password != confirm_password:
        flash("A confirmação da senha não confere.", "error")
        return redirect(url_for("pages.configuracoes"))
    current_user.password_hash = generate_password_hash(new_password)
    db.session.add(AuditLog(action="alterou senha", details="Senha do usuário principal alterada", user=current_user))
    db.session.commit()
    flash("Senha alterada com sucesso.", "success")
    return redirect(url_for("pages.configuracoes"))


# ---------------------------------------------------------------------------
# Relatório PDF
# ---------------------------------------------------------------------------

@bp.route("/relatorios/pdf")
@login_required
def relatorios_pdf():
    period = request.args.get("period", "month")
    try:
        pdf = build_pdf_report(period)
    except RuntimeError as exc:
        return str(exc), 500
    filename = f"cashflow_relatorio_{period}_{datetime.utcnow().strftime('%Y%m%d_%H%M')}.pdf"
    return send_file(pdf, mimetype="application/pdf", as_attachment=True, download_name=filename)
