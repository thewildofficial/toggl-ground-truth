<script>
  // Score trend line chart — SVG, hand-rolled. Ease-out expo per impeccable.
  let { data = [] } = $props();

  const W = 640, H = 180, pad = 28;
  let w = $derived(Math.max(W, data.length * 24));

  let points = $derived.by(() => {
    if (!data.length) return [];
    const max = 100;
    const innerW = w - pad * 2;
    const innerH = H - pad * 2;
    const step = data.length > 1 ? innerW / (data.length - 1) : 0;
    return data.map((d, i) => ({
      x: pad + i * step,
      y: pad + innerH - (d.score / max) * innerH,
      score: d.score,
      date: d.date,
    }));
  });

  let path = $derived(points.map((p, i) => `${i === 0 ? 'M' : 'L'}${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' '));
  let area = $derived(points.length ? `${path} L${points[points.length-1].x.toFixed(1)},${H-pad} L${points[0].x.toFixed(1)},${H-pad} Z` : '');
  let last = $derived(points[points.length - 1] || null);
</script>

<div class="chart-scroll">
  <svg viewBox="0 0 {w} {H}" width="100%" height={H} role="img" aria-label="Score trend over time">
    <!-- target line at 100 -->
    <line x1={pad} y1={pad} x2={w-pad} y2={pad} stroke="var(--surface-3)" stroke-width="1" stroke-dasharray="3 4" />
    {#if area}
      <path d={area} fill="var(--accent)" opacity="0.08" />
      <path d={path} fill="none" stroke="var(--accent)" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="transition: stroke-dasharray 0.6s cubic-bezier(0.2,0,0,1);" />
      {#each points as p}
        <circle cx={p.x} cy={p.y} r="3" fill="var(--bg)" stroke="var(--accent)" stroke-width="2" />
      {/each}
      {#if last}
        <circle cx={last.x} cy={last.y} r="5" fill="var(--accent)" />
      {/if}
    {/if}
  </svg>
</div>

<style>
  .chart-scroll { overflow-x: auto; scrollbar-width: thin; }
  svg { display: block; min-width: 320px; }
</style>
