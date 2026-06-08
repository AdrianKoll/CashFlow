from __future__ import annotations
from datetime import datetime, timedelta, time
from flask import request
from . import db
from .models import Transaction


# ---------------------------------------------------------------------------
# Formatação
# ---------------------------------------------------------------------------

def fmt_brl(value) -> str:
    return f"R$ {float(value or 0):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def safe_float(value, default: float = 0.0) -> float:
    try:
        if value in (None, ""):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def safe_int(value, default: int = 1) -> int:
    try:
        if value in (None, ""):
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def period_label(period: str) -> str:
    return {"today": "Hoje", "week": "Semana", "month": "Mês", "year": "Ano"}.get(period, "Periodo")


def initials(name: str) -> str:
    parts = [part for part in (name or "Usuário").replace(".", " ").split() if part]
    if not parts:
        return "U"
    if len(parts) == 1:
        return parts[0][0].upper()
    return (parts[0][0] + parts[-1][0]).upper()


# ---------------------------------------------------------------------------
# Períodos
# ---------------------------------------------------------------------------

def period_bounds(period: str):
    now = datetime.utcnow()
    today = datetime.combine(now.date(), time.min)
    if period == "today":
        return today, today + timedelta(days=1)
    if period == "week":
        return today - timedelta(days=today.weekday()), today + timedelta(days=1)
    if period == "month":
        return datetime(now.year, now.month, 1), today + timedelta(days=1)
    if period == "year":
        return datetime(now.year, 1, 1), today + timedelta(days=1)
    return None, None


def filtered_transactions(order: str = "asc"):
    period = request.args.get("period", "today")
    start, end = period_bounds(period)
    q = Transaction.query
    if start:
        q = q.filter(Transaction.created_at >= start)
    if end:
        q = q.filter(Transaction.created_at < end)
    q = q.order_by(Transaction.created_at.asc() if order == "asc" else Transaction.created_at.desc())
    return q.all(), period


def transactions_for_period(period: str, order: str = "asc"):
    start, end = period_bounds(period)
    q = Transaction.query
    if start:
        q = q.filter(Transaction.created_at >= start)
    if end:
        q = q.filter(Transaction.created_at < end)
    return q.order_by(Transaction.created_at.asc() if order == "asc" else Transaction.created_at.desc()).all()


# ---------------------------------------------------------------------------
# Serialização
# ---------------------------------------------------------------------------

def tx_item(t) -> dict:
    return {
        "id": t.id,
        "kind": t.kind,
        "title": t.title,
        "entity": t.entity,
        "amount": t.amount,
        "method": t.payment_method,
        "category_id": t.category_id,
        "category": t.category.name if t.category else "Geral",
        "time": (
            t.created_at.strftime("Hoje, %H:%M")
            if t.created_at.date() == datetime.utcnow().date()
            else t.created_at.strftime("%d/%m, %H:%M")
        ),
        "created_at": t.created_at.strftime("%d/%m/%Y %H:%M"),
    }


def fixed_record_total(item) -> float:
    total = sum(float(child.amount or 0) for child in getattr(item, "items", []) or [])
    return total if total > 0 else float(item.amount or 0)


def fixed_record_items_summary(item) -> str:
    parts = []
    for child in getattr(item, "items", []) or []:
        quantity = float(child.quantity or 1)
        unit = child.unit or "un"
        unit_price = float(child.unit_price or child.amount or 0)
        parts.append(
            f"{child.name}: {quantity:g} {unit} x {fmt_brl(unit_price)} = {fmt_brl(child.amount)}"
        )
    return "; ".join(parts)


def fixed_item(item) -> dict:
    items = sorted(getattr(item, "items", []) or [], key=lambda x: x.id or 0)
    total = fixed_record_total(item)
    return {
        "id": item.id,
        "kind": item.kind,
        "title": item.title,
        "entity": item.entity,
        "amount": total,
        "method": item.payment_method,
        "category": item.category.name if item.category else "Fixas",
        "category_id": item.category_id,
        "day_of_month": item.day_of_month,
        "active": item.active,
        "last_generated_month": item.last_generated_month or "Nunca",
        "items": [
            {
                "id": child.id,
                "name": child.name,
                "quantity": child.quantity or 1,
                "unit": child.unit or "un",
                "unit_price": child.unit_price or child.amount or 0,
                "amount": child.amount,
                "notes": child.notes or "",
            }
            for child in items
        ],
        "items_count": len(items),
    }


def product_item(item) -> dict:
    return {
        "id": item.id,
        "name": item.name,
        "unit": item.unit or "un",
        "unit_price": float(item.unit_price or 0),
        "default_quantity": float(item.default_quantity or 1),
        "active": bool(item.active),
        "notes": item.notes or "",
    }


# ---------------------------------------------------------------------------
# Gráfico
# ---------------------------------------------------------------------------

def build_chart(movs, period: str) -> dict:
    if period == "today":
        slots = [0, 6, 12, 18, 23]
        labels = ["00:00", "06:00", "12:00", "18:00", "23:59"]
        entradas, saidas, saldo = [], [], []
        for hour in slots:
            bucket = [t for t in movs if t.created_at.hour <= hour]
            ent = sum(t.amount for t in bucket if t.kind == "entrada")
            sai = sum(t.amount for t in bucket if t.kind == "saida")
            entradas.append(ent)
            saidas.append(-sai)
            saldo.append(ent - sai)
        return {"labels": labels, "entradas": entradas, "saidas": saidas, "saldo": saldo}

    if period == "week":
        labels = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
        entradas = [sum(t.amount for t in movs if t.kind == "entrada" and t.created_at.weekday() == d) for d in range(7)]
        saidas = [-sum(t.amount for t in movs if t.kind == "saida" and t.created_at.weekday() == d) for d in range(7)]
        saldo = []
        run = 0
        for e, s in zip(entradas, saidas):
            run += e + s
            saldo.append(run)
        return {"labels": labels, "entradas": entradas, "saidas": saidas, "saldo": saldo}

    if period == "year":
        month_labels = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
        entradas, saidas, saldo = [], [], []
        running = 0
        for month in range(1, 13):
            bucket = [t for t in movs if t.created_at.month == month]
            ent = sum(t.amount for t in bucket if t.kind == "entrada")
            sai = sum(t.amount for t in bucket if t.kind == "saida")
            running += ent - sai
            entradas.append(ent)
            saidas.append(-sai)
            saldo.append(running)
        return {"labels": month_labels, "entradas": entradas, "saidas": saidas, "saldo": saldo}

    labels, entradas, saidas, saldo = [], [], [], []
    grouped: dict = {}
    for t in movs:
        key = t.created_at.strftime("%d/%m")
        grouped.setdefault(key, {"entrada": 0, "saida": 0})
        grouped[key][t.kind] += t.amount
    for key, vals in grouped.items():
        labels.append(key)
        entradas.append(vals["entrada"])
        saidas.append(-vals["saida"])
        saldo.append((saldo[-1] if saldo else 0) + vals["entrada"] - vals["saida"])
    return {
        "labels": labels or ["Sem dados"],
        "entradas": entradas or [0],
        "saidas": saidas or [0],
        "saldo": saldo or [0],
    }
