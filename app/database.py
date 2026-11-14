from __future__ import annotations

import os
import subprocess
from datetime import datetime
from pathlib import Path

import sqlalchemy as sa
from flask import current_app
from sqlalchemy.engine import make_url
from werkzeug.security import generate_password_hash

from . import db
from .models import AuditLog, Category, FixedRecord, Transaction, User


# ---------------------------------------------------------------------------
# Configuração do diretório de cópias
# ---------------------------------------------------------------------------

def get_backup_dir() -> Path:
    backup_dir = Path(current_app.instance_path) / "copias"
    backup_dir.mkdir(parents=True, exist_ok=True)
    return backup_dir


# ---------------------------------------------------------------------------
# Migrações de compatibilidade
# ---------------------------------------------------------------------------

def ensure_database_columns() -> None:
    """Garante compatibilidade com bancos criados em versões anteriores.

    Bancos criados antes das colunas de quantidade/unidade dos itens recebem as
    colunas novas, com os valores antigos preservados.
    """
    inspector = sa.inspect(db.engine)
    if not inspector.has_table("fixed_record_item"):
        return
    existing = {column["name"] for column in inspector.get_columns("fixed_record_item")}

    with db.engine.begin() as conn:
        if "quantity" not in existing:
            conn.exec_driver_sql(
                "ALTER TABLE fixed_record_item ADD COLUMN quantity FLOAT DEFAULT 1"
            )
        if "unit" not in existing:
            conn.exec_driver_sql(
                "ALTER TABLE fixed_record_item ADD COLUMN unit VARCHAR(30) DEFAULT 'un'"
            )
        if "unit_price" not in existing:
            conn.exec_driver_sql(
                "ALTER TABLE fixed_record_item ADD COLUMN unit_price FLOAT DEFAULT 0"
            )
        conn.exec_driver_sql(
            "UPDATE fixed_record_item SET quantity = COALESCE(quantity, 1), "
            "unit = COALESCE(unit, 'un'), "
            "unit_price = CASE WHEN COALESCE(unit_price, 0) <= 0 "
            "THEN COALESCE(amount, 0) ELSE unit_price END"
        )


# ---------------------------------------------------------------------------
# Seed inicial
# ---------------------------------------------------------------------------

def _create_configured_admin() -> None:
    """Cria um administrador somente quando as credenciais forem fornecidas no ambiente."""
    username = os.getenv("CASHFLOW_ADMIN_USERNAME", "").strip()
    password = os.getenv("CASHFLOW_ADMIN_PASSWORD", "")
    name = os.getenv("CASHFLOW_ADMIN_NAME", "Administrador").strip() or "Administrador"

    if not username or not password:
        return
    if len(password) < 12:
        raise RuntimeError("CASHFLOW_ADMIN_PASSWORD deve ter pelo menos 12 caracteres.")
    if User.query.filter_by(username=username).first():
        return

    db.session.add(
        User(
            name=name,
            username=username,
            role="Administrador",
            password_hash=generate_password_hash(password),
        )
    )


def seed_database() -> None:
    db.create_all()
    ensure_database_columns()
    _create_configured_admin()

    if Category.query.count() == 0:
        db.session.add_all(
            [
                Category(name="Vendas", color="green", icon="arrow-up"),
                Category(name="Despesas", color="red", icon="arrow-down"),
                Category(name="Fixas", color="red", icon="lock"),
                Category(name="Produtos", color="green", icon="box"),
            ]
        )
    db.session.commit()


# ---------------------------------------------------------------------------
# Categoria "Fixas" — garante existência
# ---------------------------------------------------------------------------

def ensure_fixed_category() -> Category:
    cat = Category.query.filter_by(name="Fixas").first()
    if not cat:
        cat = Category(name="Fixas", color="red", icon="lock")
        db.session.add(cat)
        db.session.commit()
    return cat


# ---------------------------------------------------------------------------
# Geração automática de despesas recorrentes
# ---------------------------------------------------------------------------

def generate_due_fixed_records() -> int:
    """Gera automaticamente despesas recorrentes ativas uma vez por mês."""
    import calendar

    from .helpers import fixed_record_items_summary, fixed_record_total

    now = datetime.utcnow()
    month_key = now.strftime("%Y-%m")
    generated = 0

    for item in FixedRecord.query.filter_by(active=True).all():
        if item.last_generated_month == month_key:
            continue
        last_day = calendar.monthrange(now.year, now.month)[1]
        due_day = max(1, min(int(item.day_of_month or 1), last_day))
        created_at = datetime(now.year, now.month, due_day, 9, 0)
        amount = fixed_record_total(item)
        if amount <= 0:
            continue
        details = fixed_record_items_summary(item)
        tx = Transaction(
            kind=item.kind or "saida",
            title=item.title,
            entity=details or item.entity or "Despesa recorrente mensal",
            amount=amount,
            payment_method=item.payment_method or "Automático",
            category_id=item.category_id or ensure_fixed_category().id,
            created_by_id=item.created_by_id,
            created_at=created_at,
        )
        item.amount = amount
        db.session.add(tx)
        item.last_generated_month = month_key
        generated += 1

    if generated:
        db.session.add(
            AuditLog(
                action="gerou despesas recorrentes",
                details=f"{generated} registro(s) gerado(s) automaticamente",
            )
        )
        db.session.commit()

    return generated


# ---------------------------------------------------------------------------
# Cópias de segurança
# ---------------------------------------------------------------------------

class BackupError(RuntimeError):
    """Falha ao criar a cópia de segurança do banco."""


def _dump_postgres(destination: Path) -> None:
    """Gera a cópia com pg_dump (formato custom, restaurável com pg_restore)."""
    url = make_url(current_app.config["SQLALCHEMY_DATABASE_URI"])
    host = url.query.get("host") or url.host or "localhost"
    command = [
        "pg_dump",
        "--format=custom",
        "--no-owner",
        "--no-privileges",
        "--host", str(host),
        "--port", str(url.port or 5432),
        "--username", url.username or "postgres",
        "--dbname", url.database or "postgres",
        "--file", str(destination),
    ]
    environment = dict(os.environ)
    if url.password:
        # A senha vai pelo ambiente, nunca pela linha de comando.
        environment["PGPASSWORD"] = url.password
    try:
        subprocess.run(
            command, env=environment, check=True, capture_output=True, text=True, timeout=120
        )
    except FileNotFoundError as exc:
        raise BackupError("pg_dump não encontrado: instale o cliente do PostgreSQL.") from exc
    except subprocess.TimeoutExpired as exc:
        destination.unlink(missing_ok=True)
        raise BackupError("pg_dump excedeu o tempo limite de 120 segundos.") from exc
    except subprocess.CalledProcessError as exc:
        destination.unlink(missing_ok=True)
        current_app.logger.error("pg_dump falhou: %s", (exc.stderr or "").strip())
        raise BackupError("pg_dump falhou.") from exc


def create_database_copia(reason: str = "manual") -> Path:
    """Cria uma cópia de segurança do banco com pg_dump.

    Levanta BackupError se o pg_dump não existir ou falhar.
    """
    db.session.commit()
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    destination = get_backup_dir() / f"cashflow_copia_{reason}_{timestamp}.dump"
    _dump_postgres(destination)
    return destination


def latest_copia_path() -> Path | None:
    copias = sorted(
        get_backup_dir().glob("cashflow_copia_*.dump"),
        key=lambda x: x.stat().st_mtime,
        reverse=True,
    )
    return copias[0] if copias else None
