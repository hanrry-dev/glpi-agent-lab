
import { useState } from "react";
import "./App.css";
import Login from "./Login";

const suggestions = [
  { icon: "▤", text: "Quantos chamados estão abertos?" },
  { icon: "⌕", text: "Como redefinir a senha do e-mail?" },
  { icon: "＋", text: "Quero abrir um chamado" },
];

const initialTicket = {
  title: "Acesso ao e-mail corporativo",
  category: "Software",
  description: "Não consigo acessar minha conta de e-mail.",
  urgency: "Média",
};

const welcomeMessage = {
  role: "assistant",
  type: "welcome",
  text: "Olá! Sou o GLPILoto, seu assistente de suporte de TI.",
  detail:
    "Posso ajudar com procedimentos, consultas de chamados e solicitações de suporte.",
};

function normalizeText(value = "") {
  return String(value)
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .trim()
    .toLowerCase();
}

function getAnswer(message) {
  const text = normalizeText(message);

  if (text.includes("senha") || text.includes("redefinir")) {
    return {
      type: "article",
      title: "Como redefinir a senha do e-mail",
      steps: [
        "Acesse o portal de recuperação de senha da sua organização.",
        "Informe seu e-mail corporativo.",
        "Siga as instruções recebidas para criar uma nova senha.",
        "Se não conseguir concluir, solicite suporte à equipe de TI.",
      ],
      source: "Artigo demonstrativo — Base de conhecimento",
    };
  }

  if (text.includes("cancelar")) {
    return {
      type: "notice",
      title: "Solicitação cancelada",
      description:
        "Esta é uma simulação. Nenhum chamado real foi criado ou enviado ao GLPI.",
    };
  }

  if (
    text.includes("abrir chamado") ||
    text.includes("criar chamado") ||
    text.includes("novo chamado") ||
    text.includes("abrir um chamado")
  ) {
    return {
      type: "ticket",
      title: "Prévia do chamado",
      description: "Confira os dados antes de confirmar.",
    };
  }

  return {
    type: "fallback",
    title: "Vamos encontrar essa informação",
    description:
      "Ainda não encontrei uma resposta para essa pergunta. Experimente uma das sugestões disponíveis.",
  };
}

function App() {
  const [loggedIn, setLoggedIn] = useState(false);
  const [username, setUsername] = useState("");
  const [token, setToken] = useState("");
  const [loadingTickets, setLoadingTickets] = useState(false);
  const [glpiError, setGlpiError] = useState("");

  const [messages, setMessages] = useState([welcomeMessage]);
  const [input, setInput] = useState("");
  const [ticket, setTicket] = useState(initialTicket);
  const [confirmed, setConfirmed] = useState(false);

  async function fetchGlpiTickets() {
    setLoadingTickets(true);
    setGlpiError("");

    try {
      const allTickets = [];
      const limit = 100;
      let start = 0;
      let total = null;

      while (total === null || start < total) {
        const response = await fetch(
          `http://localhost:3000/api/glpi/tickets?start=${start}&limit=${limit}`,
          {
            headers: {
              Authorization: `Bearer ${token}`,
            },
          }
        );

        const result = await response.json();

        if (!response.ok) {
          throw new Error(
            result.error || "Falha ao consultar o GLPI."
          );
        }

        const batch = Array.isArray(result.tickets)
          ? result.tickets
          : [];

        allTickets.push(...batch);

        const match = String(result.contentRange || "").match(/\/(\d+)$/);

        if (match) {
          total = Number(match[1]);
        } else if (batch.length < limit) {
          break;
        }

        if (batch.length === 0) {
          break;
        }

        start += batch.length;
      }

      return allTickets;
    } catch (error) {
      const message =
        error instanceof Error
          ? error.message
          : "Não foi possível consultar o GLPI.";

      setGlpiError(message);
      return { error: message };
    } finally {
      setLoadingTickets(false);
    }
  }

  function handleLogin(user, authToken) {
    setUsername(user);
    setToken(authToken);
    setLoggedIn(true);
    setGlpiError("");
  }

  function handleLogout() {
    setLoggedIn(false);
    setUsername("");
    setToken("");
    setGlpiError("");
    resetChat();
  }

  async function sendMessage(value = input) {
    const question = value.trim();

    if (!question || loadingTickets) return;

    setInput("");

    setMessages((current) => [
      ...current,
      { role: "user", text: question },
    ]);

    const normalized = normalizeText(question);

    const asksResolved =
      /\b(resolvid|fechad|solucionad)/.test(normalized);

    const asksInService =
      /\b(em atendimento|em andamento|em tratamento)\b/.test(normalized);

    const asksOpen =
      /\b(aberto|aberta|abertos|abertas|pendente|pendentes)\b/.test(
        normalized
      );

    const asksForStats =
      asksResolved ||
      asksInService ||
      asksOpen ||
      normalized.includes("quantos chamados") ||
      normalized.includes("quantidade de chamados") ||
      normalized.includes("estatistica") ||
      normalized.includes("estatisticas") ||
      normalized.includes("resumo dos chamados");

    if (asksForStats) {
      const tickets = await fetchGlpiTickets();

      if (!Array.isArray(tickets)) {
        setMessages((current) => [
          ...current,
          {
            role: "assistant",
            type: "notice",
            title: "Não foi possível consultar o GLPI",
            description:
              tickets?.error ||
              "Verifique se o backend está rodando e se sua sessão continua válida.",
          },
        ]);
        return;
      }

      const getStatus = (item) =>
        normalizeText(
          typeof item.status === "object"
            ? item.status?.name
            : item.status
        );

      const isClosed = (status) =>
        status.includes("fechado") ||
        status.includes("resolvido") ||
        status.includes("solucionado");

      const isInService = (status) =>
        status.includes("atendimento") ||
        status.includes("andamento") ||
        status.includes("tratamento");

      const openCount = tickets.filter((item) => {
        const status = getStatus(item);

        return !isClosed(status) && !isInService(status);
      }).length;

      const inServiceCount = tickets.filter((item) =>
        isInService(getStatus(item))
      ).length;

      const resolvedOrClosedCount = tickets.filter((item) =>
        isClosed(getStatus(item))
      ).length;

      let title;
      let stats;

      if (asksResolved) {
        title = "Chamados resolvidos/fechados";
        stats = [
          {
            label: "Resolvidos/fechados",
            value: String(resolvedOrClosedCount),
          },
        ];
      } else if (asksInService) {
        title = "Chamados em atendimento";
        stats = [
          {
            label: "Em atendimento",
            value: String(inServiceCount),
          },
        ];
      } else if (asksOpen) {
        title = "Chamados abertos";
        stats = [
          {
            label: "Abertos",
            value: String(openCount),
          },
        ];
      } else {
        title = "Resumo real dos chamados";
        stats = [
          { label: "Abertos", value: String(openCount) },
          {
            label: "Em atendimento",
            value: String(inServiceCount),
          },
          {
            label: "Resolvidos/fechados",
            value: String(resolvedOrClosedCount),
          },
        ];
      }

      setMessages((current) => [
        ...current,
        {
          role: "assistant",
          type: "stats",
          title,
          description: `Dados consultados no GLPI. Total consultado: ${tickets.length} chamados.`,
          stats,
          source: "Dados reais do GLPI",
        },
      ]);

      return;
    }

    const answer = getAnswer(question);

    setMessages((current) => [
      ...current,
      { role: "assistant", ...answer },
    ]);
  }

  function resetChat() {
    setMessages([welcomeMessage]);
    setConfirmed(false);
    setTicket({ ...initialTicket });
    setInput("");
    setGlpiError("");
  }

  function confirmTicket() {
    if (confirmed) return;

    setConfirmed(true);

    setMessages((current) => [
      ...current,
      {
        role: "assistant",
        type: "notice",
        title: "Simulação concluída",
        description:
          "O fluxo de confirmação funcionou! Nenhum chamado real foi enviado ao GLPI.",
      },
    ]);
  }

  if (!loggedIn) {
    return <Login onLogin={handleLogin} />;
  }

  return (
    <main className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-icon">G</div>

          <div>
            <strong>
              GLPI<span>Loto</span>
            </strong>
            <small>IT SUPPORT ASSISTANT</small>
          </div>
        </div>

        <div className="demo-badge">
          <span className="status-dot" />
          Integração GLPI
        </div>

        <button className="new-chat" onClick={resetChat}>
          <span>＋</span> Nova conversa
        </button>

        <div className="side-label">EXPERIMENTE</div>

        <div className="suggestion-list">
          {suggestions.map((item) => (
            <button
              className="side-suggestion"
              key={item.text}
              onClick={() => sendMessage(item.text)}
              disabled={loadingTickets}
            >
              <span className="suggestion-icon">{item.icon}</span>
              <span>{item.text}</span>
            </button>
          ))}
        </div>

        <div className="sidebar-bottom">
          <div className="profile-avatar">
            {username.slice(0, 2).toUpperCase()}
          </div>

          <div className="profile-text">
            <strong>{username}</strong>
            <small>Usuário conectado</small>
          </div>

          <span className="online-dot" />

          <button
            className="logout-button"
            onClick={handleLogout}
            title="Sair da conta"
            aria-label="Sair da conta"
          >
            ↪
          </button>
        </div>
      </aside>

      <section className="chat-panel">
        <header className="topbar">
          <div>
            <div className="breadcrumb">
              Workspace <span>/</span> Assistente
            </div>

            <h1>Assistente virtual</h1>
          </div>

          <div className="connection-status">
            <span className="status-dot" />
            {loadingTickets ? "Consultando GLPI..." : "Backend conectado"}
          </div>
        </header>

        <div className="demo-banner">
          <span className="banner-icon">ⓘ</span>

          <div>
            <strong>Consulta de chamados integrada</strong>
            <p>
              As estatísticas consultam o GLPI pela API. A base de conhecimento
              e a criação de chamados ainda são demonstrativas.
            </p>
          </div>
        </div>

        {glpiError && (
          <div className="demo-banner" role="alert">
            <span className="banner-icon">!</span>
            <div>
              <strong>Erro na consulta do GLPI</strong>
              <p>{glpiError}</p>
            </div>
          </div>
        )}

        <div className="conversation" aria-live="polite">
          {messages.map((message, index) => (
            <div
              className={`message-row ${
                message.role === "user" ? "user-row" : ""
              }`}
              key={index}
            >
              {message.role === "assistant" && (
                <div className="bot-avatar">G</div>
              )}

              <div className="message-content">
                {message.role === "assistant" && (
                  <div className="message-author">
                    GLPILoto <span>Assistente</span>
                  </div>
                )}

                {message.role === "user" ? (
                  <div className="user-bubble">{message.text}</div>
                ) : (
                  <div className="bot-message">
                    {message.type === "welcome" && (
                      <>
                        <h2>{message.text}</h2>
                        <p>{message.detail}</p>

                        <div className="welcome-hint">
                          Como posso ajudar você hoje?
                        </div>

                        <div className="inline-suggestions">
                          {suggestions.map((item) => (
                            <button
                              key={item.text}
                              onClick={() => sendMessage(item.text)}
                              disabled={loadingTickets}
                            >
                              <span>{item.icon}</span> {item.text}
                            </button>
                          ))}
                        </div>
                      </>
                    )}

                    {message.type === "stats" && (
                      <>
                        <h3>{message.title}</h3>
                        <p>{message.description}</p>

                        <div className="stats-grid">
                          {message.stats.map((stat) => (
                            <div className="stat-card" key={stat.label}>
                              <strong>{stat.value}</strong>
                              <span>{stat.label}</span>
                            </div>
                          ))}
                        </div>

                        <div className="source-chip">
                          ▤ {message.source}
                        </div>
                      </>
                    )}

                    {message.type === "article" && (
                      <>
                        <h3>{message.title}</h3>

                        <ol className="steps-list">
                          {message.steps.map((step) => (
                            <li key={step}>{step}</li>
                          ))}
                        </ol>

                        <div className="source-chip">
                          ▤ {message.source}
                        </div>
                      </>
                    )}

                    {message.type === "ticket" && (
                      <>
                        <h3>{message.title}</h3>
                        <p>{message.description}</p>

                        <div className="ticket-preview">
                          <label htmlFor={`ticket-title-${index}`}>
                            Título
                          </label>

                          <input
                            id={`ticket-title-${index}`}
                            value={ticket.title}
                            onChange={(event) =>
                              setTicket({
                                ...ticket,
                                title: event.target.value,
                              })
                            }
                          />

                          <label htmlFor={`ticket-category-${index}`}>
                            Categoria
                          </label>

                          <select
                            id={`ticket-category-${index}`}
                            value={ticket.category}
                            onChange={(event) =>
                              setTicket({
                                ...ticket,
                                category: event.target.value,
                              })
                            }
                          >
                            <option>Software</option>
                            <option>Hardware</option>
                            <option>Rede</option>
                            <option>E-mail</option>
                          </select>

                          <label htmlFor={`ticket-description-${index}`}>
                            Descrição
                          </label>

                          <textarea
                            id={`ticket-description-${index}`}
                            value={ticket.description}
                            onChange={(event) =>
                              setTicket({
                                ...ticket,
                                description: event.target.value,
                              })
                            }
                          />

                          <label htmlFor={`ticket-urgency-${index}`}>
                            Urgência
                          </label>

                          <select
                            id={`ticket-urgency-${index}`}
                            value={ticket.urgency}
                            onChange={(event) =>
                              setTicket({
                                ...ticket,
                                urgency: event.target.value,
                              })
                            }
                          >
                            <option>Baixa</option>
                            <option>Média</option>
                            <option>Alta</option>
                          </select>

                          <div className="ticket-actions">
                            <button
                              className="cancel-button"
                              onClick={() =>
                                sendMessage(
                                  "Quero cancelar a abertura do chamado"
                                )
                              }
                            >
                              Cancelar
                            </button>

                            <button
                              className="confirm-button"
                              disabled={confirmed}
                              onClick={confirmTicket}
                            >
                              {confirmed
                                ? "Simulação confirmada"
                                : "Confirmar (simulação)"}
                            </button>
                          </div>

                          <small className="ticket-note">
                            Esta ação ainda não cria um chamado real.
                          </small>
                        </div>
                      </>
                    )}

                    {message.type === "fallback" && (
                      <>
                        <h3>{message.title}</h3>
                        <p>{message.description}</p>
                      </>
                    )}

                    {message.type === "notice" && (
                      <>
                        <h3>{message.title}</h3>
                        <p>{message.description}</p>
                      </>
                    )}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>

        <form
          className="composer"
          onSubmit={(event) => {
            event.preventDefault();
            sendMessage();
          }}
        >
          <div className="input-wrap">
            <input
              value={input}
              onChange={(event) => setInput(event.target.value)}
              placeholder={
                loadingTickets
                  ? "Consultando os chamados..."
                  : "Pergunte algo ao GLPILoto..."
              }
              aria-label="Mensagem para o GLPILoto"
              disabled={loadingTickets}
            />

            <span className="input-shortcut">Enter ↵</span>
          </div>

          <button
            className="send-button"
            type="submit"
            aria-label="Enviar mensagem"
            disabled={loadingTickets}
          >
            ↑
          </button>

          <p>
            O GLPILoto pode cometer erros. Confira as informações antes de
            agir.
          </p>
        </form>
      </section>
    </main>
  );
}

export default App;
