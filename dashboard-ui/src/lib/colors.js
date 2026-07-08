// Per-goal color system. Each goal has a dedicated hue for instant recognition.
// Colors chosen for: (1) distinguishability from each other, (2) contrast on dark bg,
// (3) semantic fit where possible (meditation=calm violet, fitness=energy orange).
// OKLCH-inspired hues, verified for dark-mode legibility.

export const GOAL_COLORS = {
  meditation:  '#a78bfa',  // violet — calm
  language:    '#fbbf24',  // amber — communication
  reading:     '#34d399',  // emerald — growth
  research:    '#60a5fa',  // blue — analytical (kept as the "core" color)
  learning:    '#fb7185',  // rose — curiosity
  fitness:     '#fb923c',  // orange — energy
};

export const TIER_COLORS = {
  'non-negotiable': '#a78bfa',
  'high-ideal':     '#60a5fa',
  'foundation':     '#fb923c',
};

// status colors for progress bars
export const STATUS = {
  met:    '#34d399',
  partial: '#fbbf24',
  low:    '#60a5fa',
  empty:  '#272b34',
};

export function goalColor(name) {
  return GOAL_COLORS[name] || '#60a5fa';
}

export function statusColor(pct, met) {
  if (met) return STATUS.met;
  if (pct >= 0.5) return STATUS.partial;
  if (pct > 0) return STATUS.low;
  return STATUS.empty;
}