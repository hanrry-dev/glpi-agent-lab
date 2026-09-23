"""
Cliente Python para a API v2 (High-Level API) do GLPI 11.

Squad A - Infra & Cliente GLPI
Projeto: agente de IA sobre a central de servicos.

Uso:
    from cliente import GLPIClient

    client = GLPIClient()
    print(client.get("/v2/Administration/User/Me"))

    # paginacao automatica: traz TODOS os chamados
    chamados = client.get_todos("/v2/Assistance/Ticket")
    print(len(chamados))
"""

import os
import time

import requests
from dotenv import load_dotenv

load_dotenv()


class GLPIError(Exception):
    """Erro generico do cliente GLPI."""


class GLPIAuthError(GLPIError):
    """Falha de autenticacao (credenciais invalidas, token recusado)."""


class GLPIClient:
    """Cliente da API v2 do GLPI.

    Cuida de:
      - autenticacao OAuth2 (password grant)
      - renovacao do token via refresh_token antes de expirar
      - paginacao por start/limit
      - tratamento de qualquer 2xx como sucesso (a API devolve 206 em
        listagens parciais e 200 quando a pagina cobre a colecao inteira)
    """

    def __init__(self, base_url=None, client_id=None, client_secret=None,
                 username=None, password=None, scope="api", timeout=15):
        self.base_url = (base_url or os.getenv(
            "GLPI_BASE_URL", "http://localhost:8080/api.php")).rstrip("/")
        self.client_id = client_id or os.getenv("GLPI_CLIENT_ID")
        self.client_secret = client_secret or os.getenv("GLPI_CLIENT_SECRET")
        self.username = username or os.getenv("GLPI_USERNAME", "glpi")
        self.password = password or os.getenv("GLPI_PASSWORD", "glpi")
        self.scope = scope
        self.timeout = timeout

        self.access_token = None
        self.refresh_token = None
        self.expira_em = 0.0  # timestamp unix

        if not self.client_id or not self.client_secret:
            raise GLPIError(
                "GLPI_CLIENT_ID / GLPI_CLIENT_SECRET nao configurados. "
                "Copie .env.example para .env e preencha "
                "(valores em lab/oauth-client.md)."
            )

    # ------------------------------------------------------------------
    # Autenticacao
    # ------------------------------------------------------------------
    def _pedir_token(self, payload):
        url = f"{self.base_url}/token"
        try:
            resp = requests.post(url, json=payload, timeout=self.timeout)
        except requests.RequestException as e:
            raise GLPIError(f"Nao consegui falar com o GLPI em {url}: {e}") from e

        if resp.status_code in (400, 401):
            raise GLPIAuthError(
                f"Autenticacao recusada ({resp.status_code}): {resp.text[:300]}"
            )
        if not resp.ok:
            raise GLPIError(f"Erro {resp.status_code} ao obter token: {resp.text[:300]}")

        dados = resp.json()
        self.access_token = dados["access_token"]
        self.refresh_token = dados.get("refresh_token")
        # margem de 60s para nunca usar um token que expira no meio da chamada
        self.expira_em = time.time() + dados.get("expires_in", 3600) - 60
        return dados

    def autenticar(self):
        """Login inicial com usuario e senha (password grant)."""
        return self._pedir_token({
            "grant_type": "password",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "username": self.username,
            "password": self.password,
            "scope": self.scope,
        })

    def renovar(self):
        """Renova o token usando o refresh_token.

        Se nao houver refresh_token, ou se ele ja tiver sido invalidado,
        cai de volta no login completo.
        """
        if not self.refresh_token:
            return self.autenticar()
        try:
            return self._pedir_token({
                "grant_type": "refresh_token",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "refresh_token": self.refresh_token,
                "scope": self.scope,
            })
        except GLPIAuthError:
            self.refresh_token = None
            return self.autenticar()

    def _garantir_token(self):
        if self.access_token is None:
            self.autenticar()
        elif time.time() >= self.expira_em:
            self.renovar()

    def _headers(self):
        self._garantir_token()
        # Content-Type so vai quando ha corpo (POST/PATCH). Manda-lo num
        # GET sem corpo faz o GLPI tentar interpretar um body vazio como
        # JSON e devolver 400 "Corpo JSON invalido".
        return {"Authorization": f"Bearer {self.access_token}"}

    # ------------------------------------------------------------------
    # Requisicoes
    # ------------------------------------------------------------------
    def _request(self, metodo, endpoint, params=None, json=None, _repetiu=False):
        url = f"{self.base_url}{endpoint}"
        headers = self._headers()
        if json is not None:
            headers["Content-Type"] = "application/json"
        try:
            resp = requests.request(
                metodo, url, headers=headers,
                params=params, json=json, timeout=self.timeout,
            )
        except requests.RequestException as e:
            raise GLPIError(f"Falha de rede em {metodo} {endpoint}: {e}") from e

        # token expirou antes da hora prevista -> renova e tenta de novo (1x)
        if resp.status_code == 401 and not _repetiu:
            self.renovar()
            return self._request(metodo, endpoint, params, json, _repetiu=True)

        # qualquer 2xx e sucesso: 200 pagina completa, 206 pagina parcial
        if not (200 <= resp.status_code < 300):
            raise GLPIError(
                f"{metodo} {endpoint} devolveu {resp.status_code}: {resp.text[:300]}"
            )

        if not resp.content:
            return None
        return resp.json()

    def get(self, endpoint, params=None):
        return self._request("GET", endpoint, params=params)

    def post(self, endpoint, dados=None):
        return self._request("POST", endpoint, json=dados)

    def patch(self, endpoint, dados=None):
        return self._request("PATCH", endpoint, json=dados)

    # ------------------------------------------------------------------
    # Funcoes de alto nivel (Trello: Squad A, tarefa 2)
    # ------------------------------------------------------------------
    def buscar_todos_artigos(self):
        """Todos os artigos da base de conhecimento, ja paginados por dentro."""
        return self.get_todos("/v2/Knowledgebase/Article")

    def buscar_chamados(self, filtros=None):
        """Todos os chamados, com filtro opcional aplicado no lado do cliente.

        A API do GLPI nao tem filtro server-side (?filter=, ?status= sao
        ignorados silenciosamente - ver docs/api-glpi-v2.md), entao esta
        funcao sempre pagina a colecao inteira por dentro e filtra em
        Python. Chamando sem filtros, e so um alias de get_todos.

        filtros: dict opcional, ex:
            buscar_chamados({"status": 5})          # so um status
            buscar_chamados({"status": [1, 2]})      # varios status
            buscar_chamados({"category": 3})         # so uma categoria

        As chaves usam o mesmo nome do campo do chamado (status, category,
        entity, priority, etc). Como esses campos vem como objeto
        {"id": ..., "name": ...} na API, o filtro compara pelo "id".
        """
        chamados = self.get_todos("/v2/Assistance/Ticket")
        if not filtros:
            return chamados

        def bate(chamado, campo, valor_esperado):
            valor_real = chamado.get(campo)
            if isinstance(valor_real, dict):
                valor_real = valor_real.get("id")
            if isinstance(valor_esperado, (list, tuple, set)):
                return valor_real in valor_esperado
            return valor_real == valor_esperado

        return [
            c for c in chamados
            if all(bate(c, campo, esperado) for campo, esperado in filtros.items())
        ]

    # ------------------------------------------------------------------
    # Paginacao
    # ------------------------------------------------------------------
    def get_todos(self, endpoint, limite_pagina=100, teto=None):
        """Percorre uma colecao inteira paginando por start/limit.

        A API nao tem filtro server-side: para responder "quantos chamados
        abertos de rede", pagine tudo com este metodo e filtre no Python.

        teto: para de buscar depois de N itens (util para testes rapidos).
        """
        itens = []
        start = 0
        while True:
            pagina = self.get(endpoint, params={"start": start, "limit": limite_pagina})
            if not pagina:
                break
            itens.extend(pagina)
            if len(pagina) < limite_pagina:
                break
            if teto is not None and len(itens) >= teto:
                return itens[:teto]
            start += limite_pagina
        return itens


if __name__ == "__main__":
    from collections import Counter

    client = GLPIClient()

    print("Autenticando...")
    client.autenticar()
    print("OK. Token expira em ~", int(client.expira_em - time.time()), "segundos")

    print("\nSessao atual:")
    print(client.get("/v2/session"))

    print("\nBuscando todos os chamados (buscar_chamados)...")
    chamados = client.buscar_chamados()
    print("Total de chamados:", len(chamados))

    por_status = Counter(
        c["status"]["name"] if isinstance(c.get("status"), dict) else c.get("status")
        for c in chamados
    )
    print("Distribuicao por status:", dict(por_status))

    por_categoria = Counter(
        c["category"]["name"] if isinstance(c.get("category"), dict) else c.get("category")
        for c in chamados
    )
    print("Distribuicao por categoria:", dict(por_categoria))

    print("\nBuscando artigos da base de conhecimento (buscar_todos_artigos)...")
    artigos = client.buscar_todos_artigos()
    print("Total de artigos:", len(artigos))

    print("\nExemplo de filtro (buscar_chamados com filtro de status)...")
    algum_status = chamados[0]["status"]
    algum_status_id = algum_status["id"] if isinstance(algum_status, dict) else algum_status
    filtrados = client.buscar_chamados({"status": algum_status_id})
    print(f"Chamados com status id={algum_status_id}:", len(filtrados))

    if chamados:
        print("\nFormato de um chamado (campos):")
        print(sorted(chamados[0].keys()))

    if artigos:
        print("\nFormato de um artigo (campos):")
        print(sorted(artigos[0].keys()))
