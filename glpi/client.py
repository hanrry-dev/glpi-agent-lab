"""Fachada: um método por recurso. Compõe auth + transport + writes."""
from __future__ import annotations

import requests

from .auth import TokenManager
from .config import Settings
from .errors import ClosedTicketUpdateError, GLPIError
from .routes import Routes
from .text import ensure_html, html_to_text
from .transport import Transport
from .writes import PendingWrite


class GLPIClient:
    def __init__(self, settings: Settings | None = None,
                 session: requests.Session | None = None):
        self.settings = settings or Settings.from_env()
        http = session or requests.Session()
        self.auth = TokenManager(self.settings, http)
        self.transport = Transport(self.settings, self.auth, http)

    # ------------------------------- sessão --------------------------------
    def me(self) -> dict:
        return self.transport.get(Routes.SESSION)

    # ------------------------------- chamados ------------------------------
    def list_tickets(self) -> list[dict]:
        return self.transport.get_all(Routes.TICKETS)

    def get_ticket(self, ticket_id: int) -> dict:
        return self.transport.get(Routes.ticket(ticket_id))

    def get_timeline(self, ticket_id: int) -> list[dict]:
        """Itens {"type": "Followup"|"Solution"|..., "item": {...}}."""
        return self.transport.get(Routes.timeline(ticket_id))

    def get_followups(self, ticket_id: int) -> list[dict]:
        return [t["item"] for t in self.get_timeline(ticket_id) if t.get("type") == "Followup"]

    def get_solutions(self, ticket_id: int) -> list[dict]:
        return [t["item"] for t in self.get_timeline(ticket_id) if t.get("type") == "Solution"]

    def ticket_solution_text(self, ticket_id: int) -> str | None:
        """Texto da solução mais recente, ou None. Chamado sem solução não
        deve servir de fonte de sugestão (Sprint 3)."""
        sols = self.get_solutions(ticket_id)
        if not sols:
            return None
        sols.sort(key=lambda s: s.get("date_creation") or "")
        return html_to_text(sols[-1].get("content")) or None

    # ------------------------- base de conhecimento ------------------------
    def list_articles(self) -> list[dict]:
        return self.transport.get_all(Routes.ARTICLES)

    def get_article(self, article_id: int) -> dict:
        return self.transport.get(Routes.article(article_id))

    def list_article_categories(self) -> list[dict]:
        return self.transport.get_all(Routes.ARTICLE_CATEGORIES)

    # --------------------- categorias de chamado / usuários ----------------
    def list_ticket_categories(self) -> list[dict]:
        return self.transport.get_all(Routes.TICKET_CATEGORIES)

    def get_ticket_category(self, category_id: int) -> dict:
        return self.transport.get(Routes.ticket_category(category_id))

    def list_users(self) -> list[dict]:
        return self.transport.get_all(Routes.USERS)

    def get_user(self, user_id: int) -> dict:
        return self.transport.get(Routes.user(user_id))

    # --------------------------------- escrita -----------------------------
    # Nada é enviado aqui: use prepare_* + preview() + commit().
    def prepare_ticket(self, name: str, content: str, priority: int | None = None,
                       **extra) -> PendingWrite:
        payload = {"name": name, "content": ensure_html(content)}
        if priority is not None:
            payload["priority"] = priority
        payload.update(extra)
        return PendingWrite("POST", Routes.TICKETS, payload,
                            "Criar novo chamado", _sender=self._send)

    def prepare_followup(self, ticket_id: int, content: str) -> PendingWrite:
        return PendingWrite("POST", Routes.followup(ticket_id),
                            {"content": ensure_html(content)},
                            f"Adicionar acompanhamento ao chamado #{ticket_id}",
                            _sender=self._send)

    def prepare_ticket_update(self, ticket_id: int, **fields) -> PendingWrite:
        return PendingWrite("PATCH", Routes.ticket(ticket_id), dict(fields),
                            f"Atualizar chamado #{ticket_id}", _sender=self._send)

    def _send(self, pw: PendingWrite) -> dict:
        try:
            return self.transport.request(pw.method, pw.path, json=pw.payload).json()
        except GLPIError as e:
            if pw.method == "PATCH" and e.status == 500:
                raise ClosedTicketUpdateError(e.status, e.method, e.url, e.body) from e
            raise
