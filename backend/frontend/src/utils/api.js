// In dev: Vite proxies /api → localhost:8000
// In prod: frontend is served from FastAPI, so no prefix needed
const API_BASE = import.meta.env.DEV ? '/api' : '';

class RateLimitError extends Error {
  constructor(detail) {
    super(detail);
    this.name = 'RateLimitError';
  }
}

async function handleResponse(res, fallbackMsg) {
  if (res.ok) return res.json();

  const body = await res.json().catch(() => ({}));
  const detail = body.detail || fallbackMsg;

  if (res.status === 429) throw new RateLimitError(detail);
  throw new Error(detail);
}

export async function uploadFloorPlan(file) {
  const form = new FormData();
  form.append('file', file);
  const res = await fetch(`${API_BASE}/upload`, { method: 'POST', body: form });
  return handleResponse(res, 'Upload failed');
}

export async function startAnalysis(planId) {
  const res = await fetch(`${API_BASE}/analysis/${planId}`, { method: 'POST' });
  if (res.status === 409) return res.json(); // already completed
  return handleResponse(res, 'Analysis failed');
}

export async function pollStatus(planId) {
  const res = await fetch(`${API_BASE}/analysis/${planId}/status`);
  return handleResponse(res, 'Status check failed');
}

export async function fetchReport(planId) {
  const res = await fetch(`${API_BASE}/report/${planId}`);
  return handleResponse(res, 'Report not found');
}

export async function sendChatMessage(planId, messages) {
  const res = await fetch(`${API_BASE}/chat/${planId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ plan_id: planId, messages }),
  });
  return handleResponse(res, 'Chat failed');
}

export { RateLimitError };