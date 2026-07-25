const API_BASE = 'http://localhost:8000';

export async function fetchAlerts(params = {}) {
  const query = new URLSearchParams(params).toString();
  const res = await fetch(`${API_BASE}/alerts?${query}`);
  return res.json();
}

export async function fetchAlert(alertId) {
  const res = await fetch(`${API_BASE}/alerts/${alertId}`);
  return res.json();
}

export async function submitVerdict(alertId, verdict, note = '') {
  const res = await fetch(`${API_BASE}/alerts/${alertId}/verdict`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ verdict, note }),
  });
  return res.json();
}

export async function fetchEntities(params = {}) {
  const query = new URLSearchParams(params).toString();
  const res = await fetch(`${API_BASE}/entities?${query}`);
  return res.json();
}

export async function fetchEntity(entityId) {
  const res = await fetch(`${API_BASE}/entities/${entityId}`);
  return res.json();
}

export async function fetchEntityGraph(entityId) {
  const res = await fetch(`${API_BASE}/entities/${entityId}/graph`);
  return res.json();
}

export async function fetchMetrics() {
  const res = await fetch(`${API_BASE}/metrics`);
  return res.json();
}

export async function fetchDashboard() {
  const res = await fetch(`${API_BASE}/dashboard`);
  return res.json();
}

export async function simulate(scenario) {
  const res = await fetch(`${API_BASE}/simulate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ scenario }),
  });
  return res.json();
}
