// API layer — wraps the Flask backend endpoints.
async function get(path) {
  const resp = await fetch(path);
  if (!resp.ok) throw new Error(`HTTP ${resp.status} on ${path}`);
  return resp.json();
}

export const api = {
  status: () => get('/api/status'),
  today: () => get('/api/today'),
  gaps: () => get('/api/gaps'),
  scoreHistory: (days = 14) => get(`/api/score-history?days=${days}`),
  scoreAnalytics: (days = 14) => get(`/api/score-analytics?days=${days}`),
  goalDepth: (days = 7) => get(`/api/goal-depth?days=${days}`),
  heatmap: (days = 90) => get(`/api/heatmap?days=${days}`),
  gapTrajectory: (goal, days = 14) => get(`/api/gap-trajectory?goal=${goal}&days=${days}`),
  timeAllocation: (date) => get(`/api/time-allocation?date=${date}`),
  emaScores: () => get('/api/ema-scores'),
  emaComposite: () => get('/api/ema-composite'),
  emaToday: () => get('/api/ema-today'),
  sync: async () => {
    const resp = await fetch('/api/sync', { method: 'POST' });
    return resp.json();
  },
};