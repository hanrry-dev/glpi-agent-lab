
import { useState } from "react";
import "./Login.css";

const API_URL = "http://localhost:3000/api/auth";

export default function Login({ onLogin }) {
  const [mode, setMode] = useState("login");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [loading, setLoading] = useState(false);

  function changeMode(newMode) {
    setMode(newMode);
    setError("");
    setSuccess("");
    setPassword("");
    setConfirmPassword("");
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setSuccess("");

    const normalizedUsername = username.trim();

    if (!normalizedUsername || !password) {
      setError("Preencha o usuário e a senha.");
      return;
    }

    if (mode === "register") {
      if (normalizedUsername.length < 3) {
        setError("O usuário precisa ter pelo menos 3 caracteres.");
        return;
      }

      if (password.length < 8) {
        setError("A senha precisa ter pelo menos 8 caracteres.");
        return;
      }

      if (password !== confirmPassword) {
        setError("As senhas não coincidem.");
        return;
      }
    }

    try {
      setLoading(true);

      const endpoint =
        mode === "login" ? `${API_URL}/login` : `${API_URL}/register`;

      const response = await fetch(endpoint, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          username: normalizedUsername,
          password,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        setError(data.error || "Não foi possível concluir a operação.");
        return;
      }

      if (mode === "register") {
        setSuccess("Conta criada com sucesso! Você já pode entrar.");
        setMode("login");
        setPassword("");
        setConfirmPassword("");
        return;
      }

      onLogin(data.user.username, data.token);
    } catch {
      setError(
        "Não foi possível conectar à API. Verifique se o backend está rodando na porta 3000."
      );
    } finally {
      setLoading(false);
    }
  }

  const isRegister = mode === "register";

  return (
    <main className="login-page">
      <section className="login-card">
        <div className="login-brand">
          <div className="login-logo">G</div>
          <h1>
            GLPI<span>Loto</span>
          </h1>
          <p>Suporte inteligente, simplificado.</p>
        </div>

        <div className="login-heading">
          <h2>{isRegister ? "Crie sua conta" : "Bem-vindo de volta"}</h2>
          <p>
            {isRegister
              ? "Cadastre-se para acessar o assistente."
              : "Entre com suas credenciais para continuar."}
          </p>
        </div>

        <div className="login-tabs">
          <button
            type="button"
            className={!isRegister ? "active" : ""}
            onClick={() => changeMode("login")}
            disabled={loading}
          >
            Entrar
          </button>

          <button
            type="button"
            className={isRegister ? "active" : ""}
            onClick={() => changeMode("register")}
            disabled={loading}
          >
            Criar conta
          </button>
        </div>

        <form onSubmit={handleSubmit} className="login-form">
          <label htmlFor="username">Usuário</label>
          <input
            id="username"
            type="text"
            placeholder="Digite seu usuário"
            value={username}
            onChange={(event) => setUsername(event.target.value)}
            autoComplete="username"
            minLength={isRegister ? 3 : undefined}
            required
          />

          <label htmlFor="password">Senha</label>
          <input
            id="password"
            type="password"
            placeholder={
              isRegister ? "Crie uma senha com 8 caracteres ou mais" : "Digite sua senha"
            }
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            autoComplete={isRegister ? "new-password" : "current-password"}
            minLength={isRegister ? 8 : undefined}
            required
          />

          {isRegister && (
            <>
              <label htmlFor="confirm-password">Confirmar senha</label>
              <input
                id="confirm-password"
                type="password"
                placeholder="Digite a senha novamente"
                value={confirmPassword}
                onChange={(event) => setConfirmPassword(event.target.value)}
                autoComplete="new-password"
                minLength={8}
                required
              />
            </>
          )}

          {error && (
            <p className="login-error" role="alert">
              {error}
            </p>
          )}

          {success && (
            <p className="login-success" role="status">
              {success}
            </p>
          )}

          <button
            type="submit"
            className="login-button"
            disabled={loading}
          >
            {loading
              ? "Aguarde..."
              : isRegister
                ? "Criar minha conta"
                : "Entrar"}
            {!loading && <span aria-hidden="true"> →</span>}
          </button>
        </form>

        <p className="login-footer">
          GLPILoto <span>•</span> Ambiente de demonstração
        </p>
      </section>
    </main>
  );
}
