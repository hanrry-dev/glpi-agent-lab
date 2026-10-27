"""Ciclo de vida do token OAuth2 (password -> refresh -> password)."""
from __future__ import annotations

import threading
import time

import requests

from .config import Settings
from .errors import GLPIError
from .routes import TOKEN


class TokenManager:
    MARGIN = 120  # renova 2 min antes de expirar

    def __init__(self, settings: Settings, session: requests.Session):
        self.s = settings
        self.http = session
        self._access: str | None = None
        self._refresh: str | None = None
        self._expires_at = 0.0
        # pedir token novo invalida o anterior -> serializa a renovação
        self._lock = threading.Lock()

    def get_token(self, force: bool = False) -> str:
        with self._lock:
            if (not force and self._access
                    and time.time() < self._expires_at - self.MARGIN):
                return self._access
            if self._refresh:
                try:
                    self._store(self._post({
                        "grant_type": "refresh_token",
                        "refresh_token": self._refresh,
                        "client_id": self.s.client_id,
                        "client_secret": self.s.client_secret,
                    }))
                    return self._access
                except GLPIError:
                    pass  # refresh inválido/expirado -> login completo
            self._store(self._post({
                "grant_type": "password",
                "client_id": self.s.client_id,
                "client_secret": self.s.client_secret,
                "username": self.s.username,
                "password": self.s.password,
                "scope": self.s.scope,
            }))
            return self._access

    def _post(self, body: dict) -> dict:
        url = self.s.base_url + TOKEN
        r = self.http.post(url, json=body, timeout=self.s.timeout)
        if not 200 <= r.status_code < 300:
            raise GLPIError(r.status_code, "POST", url, _body(r))
        return r.json()

    def _store(self, data: dict) -> None:
        self._access = data["access_token"]
        self._refresh = data.get("refresh_token", self._refresh)
        self._expires_at = time.time() + int(data.get("expires_in", 3600))


def _body(r: requests.Response):
    try:
        return r.json()
    except ValueError:
        return r.text[:500]
