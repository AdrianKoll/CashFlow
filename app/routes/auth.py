from flask import Blueprint, redirect, render_template, request, url_for
from flask_login import current_user, login_user, logout_user, login_required
from werkzeug.security import check_password_hash
from flask_limiter.util import get_remote_address
from .. import db, limiter
from ..models import User, AuditLog

bp = Blueprint("auth", __name__)


def _username_key() -> str:
    """Agrupa as tentativas pelo usuário alvo (ou pelo IP, se não houver usuário)."""
    username = (request.form.get("username") or "").strip().lower()
    return f"user:{username}" if username else get_remote_address()


def _failed_login(response) -> bool:
    """Só tentativas que não resultaram em login (redirecionamento) consomem o limite."""
    return response.status_code != 302


@bp.route("/login", methods=["GET", "POST"])
@limiter.limit("10 per 15 minutes", methods=["POST"], deduct_when=_failed_login)
@limiter.limit("5 per 15 minutes", methods=["POST"], key_func=_username_key,
               deduct_when=_failed_login)
def login():
    if current_user.is_authenticated:
        return redirect(url_for("pages.dashboard"))
    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            db.session.add(AuditLog(action="login", details="Acesso ao sistema", user=user))
            db.session.commit()
            return redirect(url_for("pages.dashboard"))
        error = "Usuário ou senha inválidos."
    return render_template("login.html", error=error)


@bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login"))
