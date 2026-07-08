<script>
  // Composite score donut — segmented by goal contribution.
  // Each segment = that goal's weighted ratio, colored by goal hue.
  import { goalColor } from './colors.js';

  let { score = 0, delta = null, breakdown = null } = $props();

  const size = 140;
  const stroke = 14;
  const gap = 2; // gap between segments (degrees)
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;

  // build segments from breakdown
  let segments = $derived.by(() => {
    if (!breakdown) return [];
    const entries = Object.entries(breakdown);
    const totalWeight = entries.reduce((s, [_, v]) => s + v.weight, 0);
    let acc = 0;
    return entries.map(([name, v]) => {
      const frac = (v.ratio * v.weight) / totalWeight;
      const len = frac * c;
      const offset = acc;
      acc += len;
      return { name, len, offset, color: goalColor(name), ratio: v.ratio };
    });
  });

  let color = $derived(score >= 80 ? 'var(--green)' : score >= 50 ? 'var(--yellow)' : 'var(--red)');
  let arcLen = $derived((score / 100) * c);
</script>

<div class="donut-wrap">
  <svg width={size} height={size} viewBox="0 0 {size} {size}" role="img" aria-label="Composite score {score}%">
    <!-- background track -->
    <circle cx={size/2} cy={size/2} {r} fill="none" stroke="var(--surface-2)" stroke-width={stroke} />

    {#if segments.length}
      <!-- per-goal segments -->
      {#each segments as seg, i}
        <circle
          cx={size/2} cy={size/2} {r} fill="none"
          stroke={seg.color} stroke-width={stroke}
          stroke-linecap="butt"
          stroke-dasharray="{Math.max(seg.len - 1, 0)} {c}"
          stroke-dashoffset={-seg.offset}
          transform="rotate(-90 {size/2} {size/2})"
          opacity={seg.ratio > 0 ? 0.9 : 0.15}
          style="transition: stroke-dasharray 0.6s cubic-bezier(0.2,0,0,1), opacity 0.3s ease;"
        />
      {/each}
    {:else}
      <!-- fallback: single arc -->
      <circle
        cx={size/2} cy={size/2} {r} fill="none" stroke={color} stroke-width={stroke}
        stroke-linecap="round"
        stroke-dasharray="{arcLen} {c}"
        transform="rotate(-90 {size/2} {size/2})"
        style="transition: stroke-dasharray 0.6s cubic-bezier(0.2,0,0,1);"
      />
    {/if}

    <text x="50%" y="44%" text-anchor="middle" dominant-baseline="middle" class="score-num" fill="var(--text)">{score}</text>
    <text x="50%" y="60%" text-anchor="middle" dominant-baseline="middle" class="score-pct" fill="var(--text-dim)">/ 100</text>
  </svg>

  {#if delta !== null}
    <div class="delta" class:up={delta >= 0} class:down={delta < 0}>
      {delta >= 0 ? '▲' : '▼'} {Math.abs(delta)} vs yest
    </div>
  {/if}

  {#if segments.length}
    <div class="legend">
      {#each segments as seg}
        <div class="lg-item" style:--c={seg.color}>
          <span class="lg-dot" style:background={seg.color}></span>
          <span class="lg-name">{seg.name}</span>
          <span class="lg-val">{Math.round(seg.ratio * 100)}%</span>
        </div>
      {/each}
    </div>
  {/if}
</div>

<style>
  .donut-wrap { display: flex; flex-direction: column; align-items: center; gap: var(--s-3); }
  .score-num { font-size: 2.4rem; font-weight: 700; letter-spacing: -0.03em; }
  .score-pct { font-size: 0.75rem; }
  .delta { font-size: 0.8rem; font-weight: 600; }
  .delta.up { color: var(--green); }
  .delta.down { color: var(--red); }

  .legend { display: flex; flex-wrap: wrap; gap: var(--s-2) var(--s-3); justify-content: center; margin-top: var(--s-1); }
  .lg-item { display: flex; align-items: center; gap: 4px; font-size: 0.72rem; }
  .lg-dot { width: 8px; height: 8px; border-radius: 2px; flex-shrink: 0; }
  .lg-name { color: var(--text-dim); text-transform: capitalize; }
  .lg-val { color: var(--text); font-weight: 600; font-variant-numeric: tabular-nums; }
</style>