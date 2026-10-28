
const GLPI_BASE_URL = (process.env.GLPI_BASE_URL || "http://localhost:8080")
  .replace(/\/+$/, "");

const TOKEN_URL = `${GLPI_BASE_URL}/api.php/token`;

let cachedToken = null;
let tokenExpiresAt = 0;
let refreshToken = null;
let tokenRequest = null;

class GLPIError extends Error {
  constructor(message, status) {
    super(message);
    this.name = "GLPIError";
    this.status = status;
  }
}

async function requestToken(params) {
  const response = await fetch(TOKEN_URL, {
    method: "POST",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
      Accept: "application/json",
    },
    body: new URLSearchParams(params),
    signal: AbortSignal.timeout(
      Number(process.env.GLPI_TIMEOUT || 15000)
    ),
  });

  const data = await response.json().catch(() => ({}));

  if (!response.ok || !data.access_token) {
    throw new GLPIError(
      `Falha na autenticação OAuth do GLPI (HTTP ${response.status}).`,
      response.status
    );
  }

  cachedToken = data.access_token;
  refreshToken = data.refresh_token || refreshToken;
  tokenExpiresAt = Date.now() + Number(data.expires_in || 3600) * 1000;

  return cachedToken;
}

async function getToken(forceRefresh = false) {
  if (
    !forceRefresh &&
    cachedToken &&
    tokenExpiresAt - Date.now() > 120000
  ) {
    return cachedToken;
  }

  if (tokenRequest) {
    return tokenRequest;
  }

  tokenRequest = (async () => {
    if (refreshToken) {
      try {
        return await requestToken({
          grant_type: "refresh_token",
          refresh_token: refreshToken,
          client_id: process.env.GLPI_CLIENT_ID,
          client_secret: process.env.GLPI_CLIENT_SECRET,
        });
      } catch {
        cachedToken = null;
        refreshToken = null;
      }
    }

    return requestToken({
      grant_type: "password",
      client_id: process.env.GLPI_CLIENT_ID,
      client_secret: process.env.GLPI_CLIENT_SECRET,
      username: process.env.GLPI_USERNAME,
      password: process.env.GLPI_PASSWORD,
      scope: process.env.GLPI_SCOPE || "api",
    });
  })();

  try {
    return await tokenRequest;
  } finally {
    tokenRequest = null;
  }
}

async function glpiRequest(path, retry = true) {
  const token = await getToken();

  const response = await fetch(`${GLPI_BASE_URL}/api.php/v2${path}`, {
    headers: {
      Authorization: `Bearer ${token}`,
      Accept: "application/json",
    },
    signal: AbortSignal.timeout(
      Number(process.env.GLPI_TIMEOUT || 15000)
    ),
  });

  if (response.status === 401 && retry) {
    cachedToken = null;
    tokenExpiresAt = 0;
    await getToken(true);
    return glpiRequest(path, false);
  }

  if (!response.ok && response.status !== 206) {
    throw new GLPIError(
      `A API do GLPI retornou HTTP ${response.status}.`,
      response.status
    );
  }

  return {
    data: await response.json(),
    contentRange: response.headers.get("content-range"),
  };
}

async function listTickets({ start = 0, limit = 20 } = {}) {
  const safeStart = Math.max(0, Number(start) || 0);
  const safeLimit = Math.min(100, Math.max(1, Number(limit) || 20));

  return glpiRequest(
    `/Assistance/Ticket?start=${safeStart}&limit=${safeLimit}`
  );
}

module.exports = {
  listTickets,
  GLPIError,
};
