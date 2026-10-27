"""Exceções do pacote. Sem dependências internas."""
from __future__ import annotations

from typing import Any


class ConfigError(RuntimeError):
    """Configuração ausente ou inválida (variáveis de ambiente)."""


class GLPIError(Exception):
    """Resposta não-2xx da API."""

    def __init__(self, status: int, method: str, url: str, body: Any):
        self.status, self.method, self.url, self.body = status, method, url, body
        super().__init__(f"{method} {url} -> HTTP {status}: {body}")


class APIDisabledError(GLPIError):
    """403 'The High-Level API is disabled' (o lab já vem habilitado)."""


class MissingScopeError(GLPIError):
    """403 por falta de scope OAuth no token (ex.: /Administration/User/Me)."""


class ClosedTicketUpdateError(GLPIError):
    """PATCH em chamado fechado: 500 sem detalhe. Falha esperada.
    Para registrar algo num chamado fechado, use um Followup."""
