"""Teste de fumaça (somente leitura). Rode na raiz do projeto: python smoke_test.py"""
from glpi import GLPIClient, ConfigError, count_by, html_to_text
from dotenv import load_dotenv
load_dotenv()

try:
    c = GLPIClient()
except ConfigError as e:
    raise SystemExit(f"Configuração: {e}")

print("Sessão:", c.me())

tickets = c.list_tickets()
print(f"Chamados: {len(tickets)}")
print("Por status:", dict(count_by(tickets, "status")))
print("Por categoria:", dict(count_by(tickets, "category")))

articles = c.list_articles()
print(f"Artigos: {len(articles)}")

if tickets:
    t = tickets[0]
    print(f"Chamado #{t['id']} aberto em {t['date']}")  # 'date', não date_creation
    print("Timeline:", [i["type"] for i in c.get_timeline(t["id"])])
if articles:
    print("1º artigo:\n", html_to_text(articles[0].get("content"))[:300])
