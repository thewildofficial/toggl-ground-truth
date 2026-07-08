<script>
  // Score trajectory — proper line chart with grid, axes, gradient area.
  // Hand-rolled SVG. Ease-out expo per impeccable.
  let { data = [] } = $props();

  const W = 680, H = 220, padL = 36, padR = 16, padT = 20, padB = 28;
  let w = $derived(Math.max(W, data.length * 28));

  let innerW = $derived(w - padL - padR);
  let innerH = $derived(H - padT - padB);

  let points = $derived.by(() => {
    if (!data.length) return [];
    const step = data.length > 1 ? innerW / (data.length - 1) : 0;
    return data.map((d, i) => ({
      x: padL + i * step,
      y: padT + innerH - (d.score / 100) * innerH,
      score: d.score,
      date: d.date,
    }));
  });

  let linePath = $derived(points.map((p, i) => `${i === 0 ? 'M' : 'L'}${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' '));
  let areaPath = $derived(points.length ? `${linePath} L${points[points.length-1].x.toFixed(1)},${padT+innerH} L${points[0].x.toFixed(1)},${padT+innerH} Z` : '');
  let last = $derived(points[points.length - 1] || null);

  // grid lines at 0, 25, 50, 75, 100
  let gridYs = $derived([0, 25, 50, 75, 100].map(v => ({
    y: padT + innerH - (v / 100) * innerH,
    label: v,
  })));

  // x labels: show first, middle, last date
  let xLabels = $derived.by(() => {
    if (data.length < 2) return [];
    const idxs = [0, Math.floor(data.length / 2), data.length - 1];
    return idxs.map(i => ({
      x: padL + (i / (data.length - 1)) * innerW,
      label: data[i].date.slice(5), // MM-DD
    }));
  });

  // for animated draw-in
  let pathLen = $derived(linePath ? 2000 : 0); // approximate, CSS handles it
</script>

<div class="chart-scroll">
  <svg viewBox="0 0 {w} {H}" width="100%" height={H} role="img" aria-label="Score trend over {data.length} days">
    <defs>
      <linearGradient id="areaGrad" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stop-color="var(--accent)" stop-opacity="0.18" />
        <stop offset="100%" stop-color="var(--accent)" stop-opacity="0" />
      </linearGradient>
      <linearGradient id="lineGrad" x1="0" y1="0" x2="1" y2="0">
        <stop offset="0%" stop-color="var(--accent)" stop-opacity="0.5" />
        <stop offset="50%" stop-color="var(--accent)" />
        <stop offset="100%" stop-color="#22d3ee" />
      </linearGradient>
    </defs>

    <!-- grid -->
    {#each gridYs as g}
      <line x1={padL} y1={g.y} x2={w - padR} y2={g.y} stroke="var(--surface-2)" stroke-width="1" />
      <text x={padL - 6} y={g.y + 4} text-anchor="end" class="axis-label" fill="var(--text-faint)">{g.label}</text>
    {/each}

    <!-- x labels -->
    {#each xLabels as xl}
      <text x={xl.x} y={H - 8} text-anchor="middle" class="axis-label" fill="var(--text-faint)">{xl.label}</text>
    {/each}

    <!-- area fill -->
    {#if areaPath}
      <path d={areaPath} fill="url(#areaGrad)" />
    {/if}

    <!-- line -->
    {#if linePath}
      <path d={linePath} fill="none" stroke="url(#lineGrad)" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" />
    {/if}

    <!-- data points -->
    {#each points as p, i}
      <circle cx={p.x} cy={p.y} r={i === points.length - 1 ? 5 : 3} fill={i === points.length - 1 ? 'var(--accent)' : 'var(--bg)'} stroke="var(--accent)" stroke-width={i === points.length - 1 ? 0 : 2} />
    {/each}

    <!-- last point label -->
    {#if last}
      <text x={last.x} y={last.y - 10} text-anchor="middle" class="point-label" fill="var(--text)">{last.score}</text>
    {/if}
  </svg>
</div>

<style>
  .chart-scroll { overflow-x: auto; scrollbar-width: thin; }
  svg { display: block; min-width: 340px; }
  .axis-label { font-size: 9px; font-family: var(--font); font-variant-numeric: tabular-nums; }
  .point-label { font-size: 10px; font-weight: 700; font-variant-numeric: tabular-nums; }
</style>