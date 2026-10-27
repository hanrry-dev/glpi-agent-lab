# """
# Camada de acesso à API v2 (High-Level API) do GLPI 11 do laboratório.
#
# Tudo aqui segue docs/api-glpi-v2.md e docs/glpi.http. Pontos-chave da doc:
#
# * Auth: OAuth2 em POST /api.php/token (grant "password"; renovação com
#   "refresh_token"). O token dura 1h e pedir um novo invalida o anterior.
# * Paginação: SOMENTE ?start=N&limit=M (?range= é ignorado).
# * Qualquer 2xx é sucesso (200 = cobre tudo, 206 = fatia parcial).
#   Content-Range: <inicio>-<fim>/<total> vem nos dois casos.
# * NÃO existe filtro server-side: pagine tudo e filtre no código.
# * "date" = data real de abertura do chamado (NUNCA use date_creation).
# * Comentários/solução: GET .../Timeline. Escrita: POST .../Timeline/Followup.
# * "content" de chamados/artigos/followups é HTML -> use html_to_text().
# * PATCH em chamado fechado devolve 500 genérico (falha esperada).
#
# Configuração por variáveis de ambiente (veja .env.example):
# GLPI_BASE_URL, GLPI_CLIENT_ID, GLPI_CLIENT_SECRET, GLPI_USERNAME, GLPI_PASSWORD
# """
# from __future__ import annotations
#
# import os
# import re
# import threading
# import time
# from collections import Counter
# from dataclasses import dataclass, field
# from html.parser import HTMLParser
# from typing import Any, Callable, Iterator
# from dotenv import load_dotenv
# load_dotenv()
#
# import requests
#
# # --------------------------------------------------------------------------
# # Rotas (todas relativas a {base}/api.php)
# # --------------------------------------------------------------------------
# TOKEN_ROUTE = "/api.php/token"
# V2 = "/api.php/v2"
#
#
# class Routes:
#     TICKETS = f"{V2}/Assistance/Ticket"
#     ARTICLES = f"{V2}/Knowledgebase/Article"
#     ARTICLE_CATEGORIES = f"{V2}/Knowledgebase/Category"
#     TICKET_CATEGORIES = f"{V2}/Dropdowns/ITILCategory"
#     USERS = f"{V2}/Administration/User"
#     ME = f"{V2}/session"
#     SWAGGER = f"{V2}/doc.json"  # público, mas exige a API habilitada
#
#     @staticmethod
#     def ticket(ticket_id: int) -> str:
#         return f"{Routes.TICKETS}/{ticket_id}"
#
#     @staticmethod
#     def timeline(ticket_id: int) -> str:
#         return f"{Routes.TICKETS}/{ticket_id}/Timeline"  # somente GET
#
#     @staticmethod
#     def followup(ticket_id: int) -> str:
#         return f"{Routes.TICKETS}/{ticket_id}/Timeline/Followup"  # POST
#
#     @staticmethod
#     def article(article_id: int) -> str:
#         return f"{Routes.ARTICLES}/{article_id}"
#
#     @staticmethod
#     def ticket_category(category_id: int) -> str:
#         return f"{Routes.TICKET_CATEGORIES}/{category_id}"
#
#     @staticmethod
#     def user(user_id: int) -> str:
#         return f"{Routes.USERS}/{user_id}"
#
#
# # --------------------------------------------------------------------------
# # Erros
# # --------------------------------------------------------------------------
# class GLPIError(Exception):
#     def __init__(self, status: int, method: str, url: str, body: Any):
#         self.status, self.method, self.url, self.body = status, method, url, body
#         super().__init__(f"{method} {url} -> HTTP {status}: {body}")
#
#
# class APIDisabledError(GLPIError):
#     """403 'The High-Level API is disabled' (o lab já vem habilitado)."""
#
#
# class ClosedTicketUpdateError(GLPIError):
#     """PATCH em chamado fechado: 500 sem detalhe. Falha esperada.
#     Para registrar algo num chamado fechado, use add_followup()."""
#
#
# # --------------------------------------------------------------------------
# # HTML -> texto (stdlib, sem dependências)
# # --------------------------------------------------------------------------
# class _TextExtractor(HTMLParser):
#     _BLOCK = {"p", "div", "br", "li", "ul", "ol", "tr", "h1", "h2", "h3",
#               "h4", "h5", "h6", "pre", "table"}
#
#     def __init__(self) -> None:
#         super().__init__(convert_charrefs=True)
#         self.parts: list[str] = []
#
#     def handle_starttag(self, tag, attrs):
#         if tag == "li":
#             self.parts.append("\n- ")
#         elif tag in self._BLOCK:
#             self.parts.append("\n")
#
#     def handle_endtag(self, tag):
#         if tag in self._BLOCK:
#             self.parts.append("\n")
#
#     def handle_data(self, data):
#         self.parts.append(data)
#
#
# def html_to_text(html: str | None) -> str:
#     if not html:
#         return ""
#     p = _TextExtractor()
#     p.feed(html)
#     text = "".join(p.parts).replace("\xa0", " ")
#     text = re.sub(r"[ \t]+", " ", text)
#     text = re.sub(r"\n\s*\n+", "\n\n", text)
#     return text.strip()
#
#
# # --------------------------------------------------------------------------
# # Escritas pendentes (suporte ao requisito de confirmação da Sprint 4)
# # --------------------------------------------------------------------------
# @dataclass
# class PendingWrite:
#     """Uma escrita preparada, mas NÃO enviada.
#
#     Fluxo: prepare_*() -> mostrar preview() ao usuário -> só chamar
#     commit() se houver confirmação explícita. Sem commit(), nada é gravado.
#     """
#     method: str
#     path: str
#     payload: dict
#     description: str
#     _sender: Callable[["PendingWrite"], dict] = field(repr=False, default=None)
#     committed: bool = False
#
#     def preview(self) -> str:
#         import json
#         return (f"{self.description}\n"
#                 f"  {self.method} {self.path}\n"
#                 f"  corpo: {json.dumps(self.payload, ensure_ascii=False, indent=2)}")
#
#     def commit(self) -> dict:
#         if self.committed:
#             raise RuntimeError("Escrita já confirmada anteriormente.")
#         result = self._sender(self)
#         self.committed = True
#         return result
#
#
# # --------------------------------------------------------------------------
# # Cliente
# # --------------------------------------------------------------------------
# class GLPIClient:
#     PAGE_SIZE = 200
#     TOKEN_MARGIN = 120  # renova 2 min antes de expirar
#
#     def __init__(
#         self,
#         base_url: str | None = None,
#         client_id: str | None = None,
#         client_secret: str | None = None,
#         username: str | None = None,
#         password: str | None = None,
#         timeout: float = 30.0,
#         session: requests.Session | None = None,
#     ):
#         self.base_url = (base_url or os.getenv("GLPI_BASE_URL", "http://localhost:8080")).rstrip("/")
#         self.client_id = client_id or os.environ["GLPI_CLIENT_ID"]
#         self.client_secret = client_secret or os.environ["GLPI_CLIENT_SECRET"]
#         self.username = username or os.getenv("GLPI_USERNAME", "glpi")
#         self.password = password or os.getenv("GLPI_PASSWORD", "glpi")
#         self.timeout = timeout
#         self.http = session or requests.Session()
#
#         self._access_token: str | None = None
#         self._refresh_token: str | None = None
#         self._expires_at: float = 0.0
#         # pedir token novo invalida o anterior -> serializa a renovação
#         self._auth_lock = threading.Lock()
#
#     # ---------------------------- autenticação ----------------------------
#     def _token_request(self, body: dict) -> dict:
#         url = self.base_url + TOKEN_ROUTE
#         r = self.http.post(url, json=body, timeout=self.timeout)
#         if not 200 <= r.status_code < 300:
#             raise GLPIError(r.status_code, "POST", url, _safe_body(r))
#         return r.json()
#
#     def _store_token(self, data: dict) -> None:
#         self._access_token = data["access_token"]
#         self._refresh_token = data.get("refresh_token", self._refresh_token)
#         self._expires_at = time.time() + int(data.get("expires_in", 3600))
#
#     def _password_grant(self) -> None:
#         self._store_token(self._token_request({
#             "grant_type": "password",
#             "client_id": self.client_id,
#             "client_secret": self.client_secret,
#             "username": self.username,
#             "password": self.password,
#             "scope": "api",
#         }))
#
#     def _refresh_grant(self) -> None:
#         self._store_token(self._token_request({
#             "grant_type": "refresh_token",
#             "refresh_token": self._refresh_token,
#             "client_id": self.client_id,
#             "client_secret": self.client_secret,
#         }))
#
#     def authenticate(self, force: bool = False) -> str:
#         """Garante um access_token válido (renova cedo; cai para password)."""
#         with self._auth_lock:
#             if (not force and self._access_token
#                     and time.time() < self._expires_at - self.TOKEN_MARGIN):
#                 return self._access_token
#             if self._refresh_token:
#                 try:
#                     self._refresh_grant()
#                     return self._access_token
#                 except GLPIError:
#                     pass  # refresh inválido/expirado -> login completo
#             self._password_grant()
#             return self._access_token
#
#     # ------------------------------- núcleo -------------------------------
#     def request(self, method: str, path: str, *, params: dict | None = None,
#                 json: Any = None) -> requests.Response:
#         url = self.base_url + path
#         for attempt in (1, 2):
#             token = self.authenticate(force=(attempt == 2))
#             r = self.http.request(
#                 method, url, params=params, json=json, timeout=self.timeout,
#                 headers={"Authorization": f"Bearer {token}",
#                          "Accept": "application/json"},
#             )
#             if r.status_code == 401 and attempt == 1:
#                 continue  # token invalidado/expirado: renova e tenta uma vez
#             break
#
#         if not 200 <= r.status_code < 300:  # qualquer 2xx é sucesso
#             body = _safe_body(r)
#             if r.status_code == 403 and "disabled" in str(body).lower():
#                 raise APIDisabledError(r.status_code, method, url, body)
#             raise GLPIError(r.status_code, method, url, body)
#         return r
#
#     def get(self, path: str, params: dict | None = None) -> Any:
#         return self.request("GET", path, params=params).json()
#
#     # ----------------------------- paginação ------------------------------
#     def iter_collection(self, path: str, page_size: int | None = None) -> Iterator[dict]:
#         """Percorre a coleção inteira com ?start=&limit= (nunca ?range=).
#
#         Para quando: (a) Content-Range indica que acabou, (b) não há header e
#         a página veio menor que o limit, ou (c) a página veio vazia.
#         """
#         limit = page_size or self.PAGE_SIZE
#         start = 0
#         while True:
#             r = self.request("GET", path, params={"start": start, "limit": limit})
#             page = r.json()
#             if not isinstance(page, list):
#                 raise GLPIError(r.status_code, "GET", path,
#                                 f"esperava lista, veio {type(page).__name__}")
#             yield from page
#             if not page:
#                 return
#             start += len(page)
#
#             end, total = _parse_content_range(r.headers.get("Content-Range"))
#             if total is not None:
#                 if start >= total:
#                     return
#             elif len(page) < limit:
#                 return
#
#     def get_all(self, path: str, page_size: int | None = None) -> list[dict]:
#         return list(self.iter_collection(path, page_size))
#
#     # ------------------------------ chamados ------------------------------
#     def list_tickets(self) -> list[dict]:
#         return self.get_all(Routes.TICKETS)
#
#     def get_ticket(self, ticket_id: int) -> dict:
#         return self.get(Routes.ticket(ticket_id))
#
#     def get_timeline(self, ticket_id: int) -> list[dict]:
#         """Itens {"type": "Followup"|"Solution"|..., "item": {...}}."""
#         return self.get(Routes.timeline(ticket_id))
#
#     def get_followups(self, ticket_id: int) -> list[dict]:
#         return [t["item"] for t in self.get_timeline(ticket_id) if t.get("type") == "Followup"]
#
#     def get_solutions(self, ticket_id: int) -> list[dict]:
#         return [t["item"] for t in self.get_timeline(ticket_id) if t.get("type") == "Solution"]
#
#     def ticket_solution_text(self, ticket_id: int) -> str | None:
#         """Texto da solução registrada (a mais recente), ou None se não houver.
#         Chamados sem solução NÃO devem servir de fonte de sugestão (Sprint 3)."""
#         sols = self.get_solutions(ticket_id)
#         if not sols:
#             return None
#         sols.sort(key=lambda s: s.get("date_creation") or "")
#         text = html_to_text(sols[-1].get("content"))
#         return text or None
#
#     # --------------------------- base de conhecimento ---------------------
#     def list_articles(self) -> list[dict]:
#         return self.get_all(Routes.ARTICLES)
#
#     def get_article(self, article_id: int) -> dict:
#         return self.get(Routes.article(article_id))
#
#     def list_article_categories(self) -> list[dict]:
#         return self.get_all(Routes.ARTICLE_CATEGORIES)
#
#     # ----------------------- categorias de chamado / usuários -------------
#     def list_ticket_categories(self) -> list[dict]:
#         return self.get_all(Routes.TICKET_CATEGORIES)
#
#     def get_ticket_category(self, category_id: int) -> dict:
#         return self.get(Routes.ticket_category(category_id))
#
#     def list_users(self) -> list[dict]:
#         return self.get_all(Routes.USERS)
#
#     def get_user(self, user_id: int) -> dict:
#         return self.get(Routes.user(user_id))
#
#     def me(self) -> dict:
#         return self.get(Routes.ME)
#
#     # -------------------------------- escrita -----------------------------
#     # Nada aqui é chamado automaticamente: use prepare_* + preview + commit.
#     def prepare_ticket(self, name: str, content: str, priority: int | None = None,
#                        **extra: Any) -> PendingWrite:
#         """Corpo achatado, sem envelope 'input'. 'content' é HTML."""
#         payload = {"name": name, "content": _ensure_html(content)}
#         if priority is not None:
#             payload["priority"] = priority
#         payload.update(extra)
#         return PendingWrite(
#             "POST", Routes.TICKETS, payload,
#             "Criar novo chamado", _sender=self._send_write)
#
#     def prepare_followup(self, ticket_id: int, content: str) -> PendingWrite:
#         """POST em .../Timeline/Followup (funciona até em chamado fechado)."""
#         return PendingWrite(
#             "POST", Routes.followup(ticket_id), {"content": _ensure_html(content)},
#             f"Adicionar acompanhamento ao chamado #{ticket_id}",
#             _sender=self._send_write)
#
#     def prepare_ticket_update(self, ticket_id: int, **fields: Any) -> PendingWrite:
#         """PATCH parcial. Falha (500) em chamado fechado."""
#         return PendingWrite(
#             "PATCH", Routes.ticket(ticket_id), dict(fields),
#             f"Atualizar chamado #{ticket_id}", _sender=self._send_write)
#
#     def _send_write(self, pw: PendingWrite) -> dict:
#         try:
#             r = self.request(pw.method, pw.path, json=pw.payload)
#         except GLPIError as e:
#             if pw.method == "PATCH" and e.status == 500:
#                 raise ClosedTicketUpdateError(e.status, e.method, e.url, e.body) from e
#             raise
#         return r.json()  # create/followup: {"id":..., "href":...}
#
#
# # --------------------------------------------------------------------------
# # Utilidades
# # --------------------------------------------------------------------------
# def count_by(items: list[dict], key: str) -> Counter:
#     """Agrega por um campo cujo valor é {id, name} (status, category, entity)
#     ou um valor simples. Filtro/agregação é sempre local (API não filtra)."""
#     c: Counter = Counter()
#     for it in items:
#         v = it.get(key)
#         c[(v.get("name") if isinstance(v, dict) else v) or "(sem valor)"] += 1
#     return c
#
#
# def _ensure_html(text: str) -> str:
#     return text if re.search(r"<\w+[^>]*>", text) else f"<p>{_escape(text)}</p>"
#
#
# def _escape(s: str) -> str:
#     return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
#              .replace("\n", "<br>"))
#
#
# def _parse_content_range(h: str | None) -> tuple[int | None, int | None]:
#     """'0-9/300' -> (9, 300). Tolera ausência ou formato inesperado."""
#     if not h:
#         return None, None
#     m = re.search(r"(\d+)-(\d+)/(\d+)", h)
#     return (int(m.group(2)), int(m.group(3))) if m else (None, None)
#
#
# def _safe_body(r: requests.Response) -> Any:
#     try:
#         return r.json()
#     except ValueError:
#         return r.text[:500]
#
#
# # --------------------------------------------------------------------------
# # Smoke test: python glpi_client.py   (somente leitura)
# # --------------------------------------------------------------------------
# if __name__ == "__main__":
#     c = GLPIClient()
#     print("Sessão:", c.me())
#
#     tickets = c.list_tickets()
#     print(f"Chamados: {len(tickets)}")
#     print("Por status:", dict(count_by(tickets, "status")))
#     print("Por categoria:", dict(count_by(tickets, "category")))
#
#     articles = c.list_articles()
#     print(f"Artigos: {len(articles)}")
#
#     if tickets:
#         t = tickets[0]
#         print(f"Chamado #{t['id']} aberto em {t['date']}")  # 'date', não date_creation
#         print("Itens na timeline:", [i["type"] for i in c.get_timeline(t["id"])])
#     if articles:
#         print("Texto do 1º artigo:\n", html_to_text(articles[0].get("content"))[:300])