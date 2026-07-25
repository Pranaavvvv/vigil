export function riskLevel(score) {
  if (score >= 90) return 'critical';
  if (score >= 70) return 'high';
  if (score >= 40) return 'medium';
  return 'low';
}

export function riskColor(score) {
  if (score >= 90) return '#dc2626';
  if (score >= 70) return '#ef4444';
  if (score >= 40) return '#f59e0b';
  return '#22c55e';
}

export function formatTimestamp(ts) {
  if (!ts) return '—';
  const d = new Date(ts);
  return d.toLocaleString('en-US', {
    month: 'short', day: 'numeric',
    hour: '2-digit', minute: '2-digit',
  });
}

export function formatEntityType(type) {
  return type?.replace(/_/g, ' ') || '—';
}

export function formatAnomalyType(type) {
  return type?.replace(/_/g, ' ') || '—';
}
