// Points at the local FastAPI server (backend/app/api/main.py), tunneled
// through ngrok because the router's client isolation blocks direct LAN
// access between phone and Mac. Restart with `ngrok http 8000` and update
// this URL whenever the tunnel restarts (free ngrok URLs aren't stable).
const API_BASE_URL = "https://sleet-wielder-good.ngrok-free.dev";

export async function askPandit(question) {
  const response = await fetch(`${API_BASE_URL}/ask`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "ngrok-skip-browser-warning": "true" },
    body: JSON.stringify({ question }),
  });
  if (!response.ok) {
    throw new Error(`Ask failed: ${response.status}`);
  }
  return response.json();
}
