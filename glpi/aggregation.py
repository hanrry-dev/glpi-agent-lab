"""Agregações locais (a API não filtra nem agrega no servidor)."""
from __future__ import annotations

from collections import Counter


def count_by(items: list[dict], key: str) -> Counter:
    """Conta por um campo {id, name} (status, category, entity) ou simples."""
    c: Counter = Counter()
    for it in items:
        v = it.get(key)
        c[(v.get("name") if isinstance(v, dict) else v) or "(sem valor)"] += 1
    return c
