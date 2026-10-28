# GLPILoto --- Integração com o GLPI

## Resumo

O GLPILoto é uma aplicação com frontend em React/Vite e backend em
Node.js/Express. Nesta etapa, o projeto foi integrado à API do GLPI para
consultar chamados reais usando o backend, mantendo a rota de chamados
locais existente.

## O que foi implementado

-   Integração do backend com a API REST do GLPI em
    `backend/src/glpiClient.js`.
-   Tratamento da autenticação e renovação de token necessários para
    consultar a API.
-   Paginação das consultas ao GLPI.
-   Endpoint protegido por JWT para consultar chamados do GLPI:
    `GET /api/glpi/tickets`.
-   Retorno dos chamados e de informações de paginação, incluindo
    `contentRange`.
-   Frontend React consultando o backend e carregando chamados em lotes
    de até 100, permitindo consultar até 300 chamados no fluxo atual.
-   Tratamento de erros da integração no frontend.
-   Filtros por intenção/status para apresentar contagens de chamados
    abertos, em atendimento e resolvidos/fechados.
-   Normalização de texto para facilitar o reconhecimento de perguntas
    com ou sem acentos.
-   Configuração do `.gitignore` para excluir credenciais, tokens,
    dependências e o banco local.

## Arquitetura atual

``` text
Frontend React + Vite
        |
        | requisição autenticada com JWT
        v
Backend Node.js + Express
        |
        | autenticação e requisição à API REST
        v
API do GLPI
```

O backend também mantém a integração com o banco SQLite local para as
funcionalidades existentes da aplicação.

## Tecnologias

-   React
-   Vite
-   Node.js
-   Express
-   SQLite
-   API REST do GLPI
-   JWT para proteger a rota do backend

## Endpoint adicionado

### `GET /api/glpi/tickets`

Consulta os chamados do GLPI através do backend. A rota é protegida pela
autenticação JWT já usada pela aplicação.

A resposta inclui a lista de chamados e metadados de paginação, como
`contentRange`. Em caso de falha na comunicação/autenticação com o GLPI,
o backend retorna um erro de integração em vez de tratar a consulta como
bem-sucedida.

> A rota local `GET /api/tickets` continua sendo distinta e atende aos
> dados locais da aplicação.

## Configuração local

### Backend

1.  Entre na pasta `backend`.

2.  Instale as dependências:

    ``` bash
    npm install
    ```

3.  Crie o arquivo `backend/.env` localmente com as variáveis de
    configuração exigidas pelo código de integração com o GLPI.

4.  Preencha os valores com credenciais próprias do ambiente de
    desenvolvimento. **Não coloque senhas, tokens ou segredos no
    GitHub.**

5.  Inicie o backend usando o script definido em `backend/package.json`.

### Frontend

1.  Entre na pasta `frontend`.

2.  Instale as dependências:

    ``` bash
    npm install
    ```

3.  Inicie o servidor de desenvolvimento usando o script definido em
    `frontend/package.json`.

4.  Confirme que o backend está acessível no endereço configurado para o
    frontend.

> Os comandos exatos de inicialização podem variar conforme os scripts
> presentes nos respectivos `package.json`.

## Segurança e arquivos locais

Os arquivos abaixo são locais e não devem ser enviados ao repositório:

-   `backend/.env`
-   `lab/.env`
-   `lab/.token-test.json`
-   `backend/glpiloto.db`
-   `node_modules/`
-   arquivos de log e outros segredos

O `.gitignore` da raiz contém regras para excluir os segredos e
artefatos locais listados acima. Antes de cada commit, confira:

``` bash
git status
git diff --cached --check
```

Também revise os arquivos preparados para garantir que não contenham
credenciais ou tokens.

## Limitações conhecidas nesta etapa

-   A criação de chamados reais no GLPI ainda não foi implementada.
-   A base de conhecimento e algumas funcionalidades de demonstração
    continuam sendo demonstrativas.
-   A contagem de chamados depende dos nomes de status retornados pelo
    ambiente GLPI; novos status podem exigir ajustes na classificação.
-   Os scripts de teste de API em `lab/test_oauth.py`,
    `lab/test_session.py` e `lab/test_tickets.py` ficaram fora do commit
    desta etapa e precisam de revisão antes de serem compartilhados.

## Próximos passos sugeridos

1.  Implementar a consulta de um chamado específico pelo ID.
2.  Exibir detalhes do chamado, como título, status, prioridade e data
    de abertura.
3.  Implementar a criação de chamados reais no GLPI, com validação de
    campos e permissões.
4.  Revisar os testes de integração e documentar como executá-los sem
    expor credenciais.
5.  Melhorar a validação de erros e a documentação das variáveis de
    ambiente.

## Estado desta entrega

A integração de consulta de chamados foi testada no ambiente de
desenvolvimento: o frontend conseguiu buscar dados reais através do
backend, e o fluxo de contagem por status foi validado. A branch de
trabalho usada nesta entrega é `feat/frontend-glpiloto`.
