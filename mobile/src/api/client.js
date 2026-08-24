// Points at the local FastAPI server (backend/app/api/main.py), tunneled
// through ngrok because the router's client isolation blocks direct LAN
// access between phone and Mac. Restart with `ngrok http 8000` and update
// this URL whenever the tunnel restarts (free ngrok URLs aren't stable).
const API_BASE_URL = "https://sleet-wielder-good.ngrok-free.dev";

async function request(path, { method = "GET", body, token, timeoutMs = 30000 } = {}) {
  const headers = { "Content-Type": "application/json", "ngrok-skip-browser-warning": "true" };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);

  let response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined,
      signal: controller.signal,
    });
  } catch (err) {
    if (err.name === "AbortError") throw new Error("The server is taking too long to respond. Please try again.");
    throw err;
  } finally {
    clearTimeout(timeout);
  }

  if (!response.ok) {
    const detail = await response.json().catch(() => ({}));
    throw new Error(detail.detail || `Request failed: ${response.status}`);
  }
  return response.status === 204 ? null : response.json();
}

export function askPandit(question) {
  return request("/ask", { method: "POST", body: { question } });
}

export function signup(email, password, displayName) {
  return request("/auth/signup", { method: "POST", body: { email, password, display_name: displayName } });
}

export function login(email, password) {
  return request("/auth/login", { method: "POST", body: { email, password } });
}

export function listSaved(token) {
  return request("/library/saved", { token });
}

export function saveVerse(verseId, note, token) {
  return request("/library/saved", { method: "POST", body: { verse_id: verseId, note }, token });
}

export function unsaveVerse(verseId, token) {
  return request(`/library/saved/${verseId}`, { method: "DELETE", token });
}

export function listChapters() {
  return request("/library/chapters");
}

export function getProgress(token) {
  return request("/library/progress", { token });
}

export function setProgress(scripture, chapter, verseNumber, token) {
  return request("/library/progress", {
    method: "POST",
    body: { scripture, chapter, verse_number: verseNumber },
    token,
  });
}
