"""HTTP autenticado: request com retry de 401, mapeamento de erros e paginação."""
from __future__ import annotations

import re
from typing import Any, Iterator

import requests

from .auth import TokenManager
from .config import Settings
from .errors import APIDisabledError, GLPIError, MissingScopeError

PAGE_SIZE = 200


class Transport:
    def __init__(self, settings: Settings, auth: TokenManager, session: requests.Session):
        self.s, self.auth, self.http = settings, auth, session

    # --------------------------- requisição base ---------------------------
    def request(self, method: str, path: str, *, params: dict | None = None,
                json: Any = None) -> requests.Response:
        url = self.s.base_url + path
        for attempt in (1, 2):
            token = self.auth.get_token(force=(attempt == 2))
            r = self.http.request(
                method, url, params=params, json=json, timeout=self.s.timeout,
                headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
            )
            if r.status_code == 401 and attempt == 1:
                continue  # token invalidado/expirado: renova e tenta uma vez
            break

        if not 200 <= r.status_code < 300:  # qualquer 2xx é sucesso (200/206/201)
            raise self._to_error(r, method, url)
        return r

    def get(self, path: str, params: dict | None = None) -> Any:
        return self.request("GET", path, params=params).json()

    # ------------------------------ paginação ------------------------------
    def iter_collection(self, path: str, page_size: int = PAGE_SIZE) -> Iterator[dict]:
        """?start=&limit= (nunca ?range=). Para quando o Content-Range indica o
        fim; sem header, quando a página vem menor que o limit; ou vazia."""
        start = 0
        while True:
            r = self.request("GET", path, params={"start": start, "limit": page_size})
            page = r.json()
            if not isinstance(page, list):
                raise GLPIError(r.status_code, "GET", path,
                                f"esperava lista, veio {type(page).__name__}")
            yield from page
            if not page:
                return
            start += len(page)

            total = parse_content_range(r.headers.get("Content-Range"))[1]
            if total is not None:
                if start >= total:
                    return
            elif len(page) < page_size:
                return

    def get_all(self, path: str, page_size: int = PAGE_SIZE) -> list[dict]:
        return list(self.iter_collection(path, page_size))

    # -------------------------------- erros --------------------------------
    @staticmethod
    def _to_error(r: requests.Response, method: str, url: str) -> GLPIError:
        try:
            body = r.json()
        except ValueError:
            body = r.text[:500]
        text = str(body).lower()
        if r.status_code == 403 and "disabled" in text:
            return APIDisabledError(r.status_code, method, url, body)
        if r.status_code == 403 and "scope" in text:
            return MissingScopeError(r.status_code, method, url, body)
        return GLPIError(r.status_code, method, url, body)


def parse_content_range(h: str | None) -> tuple[int | None, int | None]:
    """'0-9/300' -> (9, 300). Tolera ausência ou formato inesperado."""
    if not h:
        return None, None
    m = re.search(r"(\d+)-(\d+)/(\d+)", h)
    return (int(m.group(2)), int(m.group(3))) if m else (None, None)
