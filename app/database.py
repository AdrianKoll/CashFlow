from __future__ import annotations
import shutil
from datetime import datetime
from pathlib import Path
from flask import current_app
from werkzeug.security import generate_password_hash
from . import db
from .models import User, Category, FixedRecord, Transaction, AuditLog


# ---------------------------------------------------------------------------
# Configuração do diretório de cópias
# ---------------------------------------------------------------------------

def get_backup_dir() -> Path:
    backup_dir = Path(current_app.instance_path) / "copias"
    backup_dir.mkdir(parents=True, exist_ok=True)
    return backup_dir


def get_sqlite_path() -> Path:
    uri = current_app.config.get("SQLALCHEMY_DATABASE_URI", "")
    if uri.startswith("sqlite:///"):
        db_name = uri.replace("sqlite:///", "", 1)
        db_path = Path(db_name)
        if not db_path.is_absolute():
            return Path(current_app.instance_path) / db_name
        return db_path
    return Path(current_app.instance_path) / "cashflow_dados.sqlite3"


# ---------------------------------------------------------------------------
# Migrações de compatibilidade
# ---------------------------------------------------------------------------

def ensure_database_columns() -> None:
    """Garante compatibilidade com bancos SQLite criados em versões anteriores."""
    with db.engine.begin() as conn:
        existing = {row[1] for row in conn.exec_driver_sql("PRAGMA table_info(fixed_record_item)").fetchall()}
        if existing:
            if "quantity" not in existing:
                conn.exec_driver_sql("ALTER TABLE fixed_record_item ADD COLUMN quantity FLOAT DEFAULT 1")
            if "unit" not in existing:
                conn.exec_driver_sql("ALTER TABLE fixed_record_item ADD COLUMN unit VARCHAR(30) DEFAULT 'un'")
            if "unit_price" not in existing:
                conn.exec_driver_sql("ALTER TABLE fixed_record_item ADD COLUMN unit_price FLOAT DEFAULT 0")
            conn.exec_driver_sql(
                "UPDATE fixed_record_item SET quantity = COALESCE(quantity, 1), "
                "unit = COALESCE(unit, 'un'), "
                "unit_price = CASE WHEN COALESCE(unit_price, 0) <= 0 "
                "THEN COALESCE(amount, 0) ELSE unit_price END"
            )


# ---------------------------------------------------------------------------
# Seed inicial
# ---------------------------------------------------------------------------

def seed_database() -> None:
    db.create_all()
    ensure_database_columns()
    if not User.query.filter_by(username="caixa").first():
        db.session.add(User(
            name="Usuário Principal",
            username="caixa",
            role="Administrador",
            password_hash=generate_password_hash("caixa1020"),
        ))
    if Category.query.count() == 0:
        db.session.add_all([
            Category(name="Vendas", color="green", icon="arrow-up"),
            Category(name="Despesas", color="red", icon="arrow-down"),
            Category(name="Fixas", color="red", icon="lock"),
            Category(name="Produtos", color="green", icon="box"),
        ])
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
    from .helpers import fixed_record_total, fixed_record_items_summary

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
        db.session.add(AuditLog(
            action="gerou despesas recorrentes",
            details=f"{generated} registro(s) gerado(s) automaticamente",
        ))
        db.session.commit()

    return generated


# ---------------------------------------------------------------------------
# Cópias de segurança
# ---------------------------------------------------------------------------

def create_database_copia(reason: str = "manual") -> Path | None:
    db.session.commit()
    source = get_sqlite_path()
    if not source.exists():
        return None
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"cashflow_copia_{reason}_{timestamp}.sqlite3"
    destination = get_backup_dir() / filename
    shutil.copy2(source, destination)
    return destination


def latest_copia_path() -> Path | None:
    backup_dir = get_backup_dir()
    copias = sorted(backup_dir.glob("cashflow_copia_*.sqlite3"), key=lambda x: x.stat().st_mtime, reverse=True)
    return copias[0] if copias else None
