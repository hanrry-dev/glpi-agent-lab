"""Leitura de configuração a partir de variáveis de ambiente (.env opcional)."""
from __future__ import annotations

import os
from dataclasses import dataclass

from .errors import ConfigError

try:  # python-dotenv é opcional: se existir, carrega o .env automaticamente
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


@dataclass(frozen=True)
class Settings:
    client_id: str
    client_secret: str
    base_url: str = "http://localhost:8080"
    username: str = "glpi"
    password: str = "glpi"
    scope: str = "api"
    timeout: float = 30.0

    @classmethod
    def from_env(cls) -> "Settings":
        missing = [k for k in ("GLPI_CLIENT_ID", "GLPI_CLIENT_SECRET") if not os.getenv(k)]
        if missing:
            raise ConfigError(
                f"Variáveis ausentes: {', '.join(missing)}. Copie .env.example para "
                ".env (valores em lab/oauth-client.md) e instale python-dotenv, "
                "ou defina-as no ambiente."
            )
        return cls(
            client_id=os.environ["GLPI_CLIENT_ID"],
            client_secret=os.environ["GLPI_CLIENT_SECRET"],
            base_url=os.getenv("GLPI_BASE_URL", "http://localhost:8080").rstrip("/"),
            username=os.getenv("GLPI_USERNAME", ""),
            password=os.getenv("GLPI_PASSWORD", ""),
            scope=os.getenv("GLPI_SCOPE", "api"),
            timeout=float(os.getenv("GLPI_TIMEOUT", "30")),
        )
