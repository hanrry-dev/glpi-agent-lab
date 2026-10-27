"""Escritas pendentes: base do requisito de confirmação da Sprint 4."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Callable


@dataclass
class PendingWrite:
    """Escrita preparada, mas NÃO enviada.

    Fluxo: prepare_*() -> mostrar preview() -> commit() só com confirmação
    explícita. Sem commit(), nada é gravado.
    """
    method: str
    path: str
    payload: dict
    description: str
    _sender: Callable[["PendingWrite"], dict] = field(repr=False, default=None)
    committed: bool = False

    def preview(self) -> str:
        return (f"{self.description}\n"
                f"  {self.method} {self.path}\n"
                f"  corpo: {json.dumps(self.payload, ensure_ascii=False, indent=2)}")

    def commit(self) -> dict:
        if self.committed:
            raise RuntimeError("Escrita já confirmada anteriormente.")
        result = self._sender(self)
        self.committed = True
        return result
