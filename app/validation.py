"""Validação de entrada da API.

Tudo que chega do cliente é tratado como não confiável: tipos, tamanhos e
faixas de valores são conferidos antes de tocar no banco. Assim, dados inválidos
viram uma resposta 400 clara (e não um erro 500 do PostgreSQL), e valores como
NaN ou infinito nunca chegam a ser salvos.
"""
from __future__ import annotations

import math
import re

from flask import request

from .models import Category

MAX_MONEY = 1_000_000_000.0   # R$ 1 bilhão por valor
MAX_QUANTITY = 1_000_000.0
MAX_ITEMS_PER_RECORD = 200
KINDS = ("entrada", "saida")
_MONTH_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


class ValidationError(Exception):
    """Entrada inválida; a mensagem é mostrada ao usuário (resposta 400)."""


def json_object() -> dict:
    """Corpo da requisição, que precisa ser um objeto JSON."""
    data = request.get_json(force=True)
    if not isinstance(data, dict):
        raise ValidationError("O corpo da requisição deve ser um objeto JSON.")
    return data


def number(value, label: str, *, minimum: float = 0.0, maximum: float = MAX_MONEY,
           positive: bool = False, default: float | None = None) -> float:
    """Número finito dentro da faixa; texto numérico ("12.5") também é aceito."""
    if value is None or value == "":
        if default is not None:
            return default
        raise ValidationError(f"{label} é obrigatório.")
    if isinstance(value, bool):
        raise ValidationError(f"{label} inválido.")
    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError):
        raise ValidationError(f"{label} inválido.") from None
    if not math.isfinite(result):
        raise ValidationError(f"{label} inválido.")
    if positive and result <= 0:
        raise ValidationError(f"{label} deve ser maior que zero.")
    if result < minimum or result > maximum:
        raise ValidationError(f"{label} fora do intervalo permitido.")
    return result


def text(value, label: str, *, max_length: int, required: bool = False,
         default: str = "") -> str:
    """Texto sem espaços nas pontas e com tamanho máximo (o da coluna)."""
    if value is None:
        value = default
    if not isinstance(value, str):
        raise ValidationError(f"{label} deve ser um texto.")
    value = value.strip()
    if required and not value:
        raise ValidationError(f"{label} é obrigatório.")
    if len(value) > max_length:
        raise ValidationError(f"{label} deve ter no máximo {max_length} caracteres.")
    return value


def kind(value) -> str:
    if value not in KINDS:
        raise ValidationError('Tipo inválido: use "entrada" ou "saida".')
    return value


def category_id(value) -> int | None:
    """Id de uma categoria que exista, ou None."""
    if value in (None, ""):
        return None
    if isinstance(value, bool) or not isinstance(value, (int, str)):
        raise ValidationError("Categoria inválida.")
    try:
        number_value = int(value)
    except ValueError:
        raise ValidationError("Categoria inválida.") from None
    if not 0 < number_value < 2**31 or db_category_missing(number_value):
        raise ValidationError("Categoria inválida.")
    return number_value


def db_category_missing(identifier: int) -> bool:
    return Category.query.filter_by(id=identifier).first() is None


def day_of_month(value, default: int = 1) -> int:
    if value in (None, ""):
        return default
    if isinstance(value, bool):
        raise ValidationError("Dia do mês inválido.")
    try:
        day = int(value)
    except (TypeError, ValueError):
        raise ValidationError("Dia do mês inválido.") from None
    if not 1 <= day <= 31:
        raise ValidationError("O dia do mês deve estar entre 1 e 31.")
    return day


def month_key(value) -> str:
    """Mês no formato AAAA-MM, ou vazio."""
    if value in (None, ""):
        return ""
    if not isinstance(value, str) or not _MONTH_RE.match(value):
        raise ValidationError("Mês inválido: use o formato AAAA-MM.")
    return value
