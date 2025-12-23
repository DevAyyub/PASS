const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:5000/api";

export function getToken() {
  return localStorage.getItem("pass_token");
}

export function setToken(token) {
  localStorage.setItem("pass_token", token);
}

export function clearToken() {
  localStorage.removeItem("pass_token");
  localStorage.removeItem("pass_role");
}

export async function api(path, { method="GET", body, token } = {}) {
  const headers = { "Content-Type": "application/json" };
  const t = token || getToken();
  if (t) headers["Authorization"] = `Bearer ${t}`;

  const res = await fetch(`${API_BASE}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined
  });

  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const msg = data?.error || `Request failed (${res.status})`;
    throw new Error(msg);
  }
  return data;
}
