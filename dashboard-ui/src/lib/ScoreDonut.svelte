<script>
  // Composite score donut — SVG, no chart lib.
  let { score = 0, delta = null } = $props();

  const size = 132;
  const stroke = 12;
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;

  let dash = $derived((score / 100) * c);
  let color = $derived(score >= 80 ? 'var(--green)' : score >= 50 ? 'var(--yellow)' : 'var(--red)');
</script>

<div class="donut-wrap">
  <svg width={size} height={size} viewBox="0 0 {size} {size}" role="img" aria-label="Composite score {score}%">
    <circle cx={size/2} cy={size/2} {r} fill="none" stroke="var(--surface-3)" stroke-width={stroke} />
    <circle
      cx={size/2} cy={size/2} {r} fill="none" stroke={color} stroke-width={stroke}
      stroke-linecap="round"
      stroke-dasharray="{dash} {c}"
      transform="rotate(-90 {size/2} {size/2})"
      style="transition: stroke-dasharray 0.6s cubic-bezier(0.2,0,0,1), stroke 0.3s ease;"
    />
    <text x="50%" y="46%" text-anchor="middle" dominant-baseline="middle" class="score-num" fill="var(--text)">{score}</text>
    <text x="50%" y="62%" text-anchor="middle" dominant-baseline="middle" class="score-pct" fill="var(--text-dim)">/100</text>
  </svg>
  {#if delta !== null}
    <div class="delta" class:up={delta >= 0} class:down={delta < 0}>
      {delta >= 0 ? '▲' : '▼'} {Math.abs(delta)} vs yest
    </div>
  {/if}
</div>

<style>
  .donut-wrap { display: flex; flex-direction: column; align-items: center; gap: var(--s-2); }
  .score-num { font-size: 2.2rem; font-weight: 700; letter-spacing: -0.03em; }
  .score-pct { font-size: 0.8rem; }
  .delta { font-size: 0.78rem; font-weight: 600; }
  .delta.up { color: var(--green); }
  .delta.down { color: var(--red); }
</style>
