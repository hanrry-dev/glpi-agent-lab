# Relatório da Sprint 0 - Reconhecimento

Este relatório apresenta as métricas iniciais extraídas do ambiente de laboratório GLPI via API, em cumprimento aos requisitos da Sprint 0. A extração foi realizada de forma automatizada utilizando o script Python anexo ao repositório.

## 📊 Métricas da Base de Dados

* **Total de chamados:** 300
* **Total de artigos na base de conhecimento:** 40

### Distribuição de Chamados por Categoria
* **Rede e Conectividade:** 102
* **Acessos e Senhas:** 69
* **Sistema ERP:** 43
* **Impressão:** 37
* **E-mail e Colaboração:** 31
* **Equipamentos:** 18

### Distribuição de Chamados por Status
* **Fechado:** 176
* **Em atendimento (atribuído):** 50
* **Solucionado:** 42
* **Novo:** 32

---

## 📝 Formato dos Dados (JSON)

Abaixo estão as estruturas padrão de resposta da API para os objetos de Chamado e Artigo da Base de Conhecimento, mapeadas durante a exploração.

### Formato de um Chamado (Ticket)
Os chamados (`Assistance/Ticket`) trazem os identificadores, conteúdo em HTML, e relacionamentos expandidos (como categoria e status sendo objetos, não apenas IDs). O campo `team` lista os envolvidos.

```json
{
  "id": 1,
  "name": "Problema ao conectar na VPN corporativa",
  "content": "<p>Minha conexão cai após alguns minutos de uso.</p>",
  "status": {
    "id": 1,
    "name": "Novo"
  },
  "priority": 3,
  "urgency": 3,
  "impact": 3,
  "category": {
    "id": 12,
    "name": "Rede e Conectividade"
  },
  "entity": {
    "id": 0,
    "name": "Root entity"
  },
  "date": "2023-01-15 09:30:00",
  "date_creation": "2024-03-20 12:05:00",
  "date_mod": "2024-03-20 12:05:00",
  "team": [
    {
      "role": "requester",
      "name": "ana.ribeiro",
      "realname": "Ribeiro",
      "firstname": "Ana",
      "display_name": "Ribeiro Ana",
      "id": 7,
      "type": "User"
    }
  ]
}