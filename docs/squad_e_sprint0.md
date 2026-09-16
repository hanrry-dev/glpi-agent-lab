# Documentação Sprint 0 - Squad E: Ações de Escrita

## 1. Mapeamento de Requisitos (API do GLPI)

Para que o agente de IA execute ações de escrita via cliente Python, foram mapeados os seguintes campos e rotas da API com base na interface do GLPI:

### A. Criação de Chamados (`POST /Ticket`)
* **`name` (Título):** Resumo objetivo do problema gerado pela IA.
* **`content` (Descrição):** Detalhamento do problema extraído da conversa com o usuário.
* **`type`:** Classificação do tipo de chamado (`1` = Incidente, `2` = Requisição).
* **`itilcategories_id`:** ID numérico da categoria correspondente (ex: *Acessos e Senhas*).
* **`urgency` e `impact`:** Níveis numéricos (1 a 5) inferidos pela IA para cálculo automático da prioridade.

### B. Adição de Acompanhamentos (`POST /ITILFollowup`)
* **`tickets_id`:** ID do chamado alvo (ex: `#301`).
* **`content`:** Texto da resposta ou atualização a ser adicionada ao histórico.

---

## 2. Análise de Riscos (Operação Sem Confirmação)

Permitir que o LLM execute requisições de escrita diretamente na API sem validação humana (*Human-in-the-Loop*) apresenta riscos críticos:

* **Escalonamento Indevido:** Classificação incorreta de urgência/impacto, disparando alertas de alta prioridade e violando métricas de SLA.
* **Erros de Payload (`400 Bad Request`):** Envio de textos arbitrários em campos relacionais que exigem estritamente IDs numéricos válidos do GLPI.
* **Injeção e Vazamento de Dados:** Inserção acidental de dados sensíveis ou informações inconsistentes nos comentários públicos do chamado.
* **Loops de Requisições:** Falhas de execução no agente de IA que podem gerar criações em massa de chamados duplicados, sobrecarregando o banco de dados.

---

## 3. Diretrizes Arquiteturais (Sprint 1)

* **Padrão Human-in-the-Loop:** A IA deve apenas construir o rascunho do pacote de dados (payload) e exibir uma prévia de confirmação.
* **Gatilho de Execução:** O método `POST` para a API do GLPI só será chamado após a autorização explícita do usuário.