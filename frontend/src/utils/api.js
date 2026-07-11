const API_BASE = '/api';

export async function uploadFloorPlan(file) {
  const form = new FormData();
  form.append('file', file);
  const res = await fetch(`${API_BASE}/upload`, { method: 'POST', body: form });
  if (!res.ok) throw new Error((await res.json()).detail || 'Upload failed');
  return res.json();
}

export async function startAnalysis(planId) {
  const res = await fetch(`${API_BASE}/analysis/${planId}`, { method: 'POST' });
  if (!res.ok && res.status !== 409) throw new Error((await res.json()).detail || 'Analysis failed');
  return res.json();
}

export async function pollStatus(planId) {
  const res = await fetch(`${API_BASE}/analysis/${planId}/status`);
  if (!res.ok) throw new Error((await res.json()).detail || 'Status check failed');
  return res.json();
}

export async function fetchReport(planId) {
  const res = await fetch(`${API_BASE}/report/${planId}`);
  if (!res.ok) throw new Error((await res.json()).detail || 'Report not found');
  return res.json();
}

export async function sendChatMessage(planId, messages) {
  const res = await fetch(`${API_BASE}/chat/${planId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ plan_id: planId, messages }),
  });
  if (!res.ok) throw new Error((await res.json()).detail || 'Chat failed');
  return res.json();
}