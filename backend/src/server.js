
require("dotenv").config();

const express = require("express");
const cors = require("cors");
const bcrypt = require("bcryptjs");
const jwt = require("jsonwebtoken");
const { listTickets, GLPIError } = require("./glpiClient");

const db = require("./database");

const app = express();
const PORT = process.env.PORT || 3000;
const JWT_SECRET = process.env.JWT_SECRET;

if (!JWT_SECRET) {
  throw new Error("JWT_SECRET não foi configurado no arquivo .env");
}

app.use(cors());
app.use(express.json());

// Rota inicial
app.get("/", (req, res) => {
  res.json({ message: "API do GLPILoto funcionando!" });
});

// Cadastro de usuário
app.post("/api/auth/register", (req, res) => {
  const { username, password } = req.body;

  if (
    typeof username !== "string" ||
    typeof password !== "string" ||
    username.trim().length < 3 ||
    password.length < 8
  ) {
    return res.status(400).json({
      error: "Informe um usuário com pelo menos 3 caracteres e uma senha com pelo menos 8 caracteres.",
    });
  }

  const normalizedUsername = username.trim();

  const existingUser = db
    .prepare("SELECT id FROM users WHERE username = ?")
    .get(normalizedUsername);

  if (existingUser) {
    return res.status(409).json({
      error: "Esse usuário já está cadastrado.",
    });
  }

  const passwordHash = bcrypt.hashSync(password, 12);

  const result = db
    .prepare("INSERT INTO users (username, password_hash) VALUES (?, ?)")
    .run(normalizedUsername, passwordHash);

  return res.status(201).json({
    message: "Usuário cadastrado com sucesso!",
    user: {
      id: result.lastInsertRowid,
      username: normalizedUsername,
    },
  });
});

// Login
app.post("/api/auth/login", (req, res) => {
  const { username, password } = req.body;

  if (
    typeof username !== "string" ||
    typeof password !== "string"
  ) {
    return res.status(400).json({
      error: "Informe o usuário e a senha.",
    });
  }

  const user = db
    .prepare("SELECT * FROM users WHERE username = ?")
    .get(username.trim());

  if (!user || !bcrypt.compareSync(password, user.password_hash)) {
    return res.status(401).json({
      error: "Usuário ou senha inválidos.",
    });
  }

  const token = jwt.sign(
    { id: user.id, username: user.username },
    JWT_SECRET,
    { expiresIn: "1h" }
  );

  return res.json({
    message: "Login realizado com sucesso!",
    token,
    user: {
      id: user.id,
      username: user.username,
    },
  });
});

// Listar chamados
app.get("/api/tickets", (req, res) => {
  const tickets = db.prepare(`
    SELECT * FROM tickets
    ORDER BY created_at DESC
  `).all();

  res.json(tickets);
});


 // Listar chamados reais do GLPI (rota protegida por JWT)
app.get("/api/glpi/tickets", async (req, res) => {
  const authHeader = req.headers.authorization;
  const token = authHeader?.startsWith("Bearer ")
    ? authHeader.slice(7)
    : null;

  if (!token) {
    return res.status(401).json({
      error: "Token de autenticação não informado.",
    });
  }

  try {
    jwt.verify(token, JWT_SECRET);
  } catch {
    return res.status(401).json({
      error: "Token inválido ou expirado. Faça login novamente.",
    });
  }

  try {
    const { data, contentRange } = await listTickets({
      start: req.query.start,
      limit: req.query.limit,
    });

    return res.json({
      tickets: Array.isArray(data) ? data : data?.data ?? [],
      contentRange,
    });
  } catch (error) {
    if (error instanceof GLPIError) {
      if (error.status === 401) {
        return res.status(502).json({
          error: "Falha de autenticação entre o backend e o GLPI.",
        });
      }

      if (error.status === 403) {
        return res.status(502).json({
          error: "O GLPI negou o acesso. Verifique as permissões do cliente.",
        });
      }
    }

    console.error("Erro ao consultar chamados do GLPI:", error.message);

    return res.status(502).json({
      error: "Não foi possível consultar os chamados do GLPI.",
    });
  }
});


app.listen(PORT, () => {
  console.log(`GLPILoto API rodando em http://localhost:${PORT}`);
});
