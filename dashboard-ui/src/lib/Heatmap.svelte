<script>
  // Per-goal heatmap — github-style density grid.
  // Each goal row uses ITS OWN color (not monochrome blue).
  // Bigger cells (14px), visible empty state, weekday alignment.
  import { goalColor } from './colors.js';

  let { heatmap } = $props();

  const COLS = 14;

  function rows(cells) {
    const out = [];
    for (let i = 0; i < cells.length; i += COLS) out.push(cells.slice(i, i + COLS));
    return out;
  }

  function cellColor(ratio, hue) {
    if (ratio <= 0) return 'var(--surface-2)';
    const opacity = 0.2 + ratio * 0.8;
    return `${hue}${Math.round(opacity * 255).toString(16).padStart(2, '0')}`;
  }
</script>

<div class="hm">
  {#each Object.entries(heatmap.goals) as [name, cellsArr]}
    <div class="hm-row">
      <div class="hm-label" style:--c={goalColor(name)}>
        <span class="hm-dot" style:background={goalColor(name)}></span>
        <span>{name}</span>
      </div>
      <div class="hm-grid">
        {#each rows(cellsArr) as row}
          <div class="hm-week">
            {#each row as cell, i}
              <div
                class="hm-cell"
                style:background={cellColor(cell, goalColor(name))}
                title="{name}: {Math.round(cell*100)}% on {heatmap.dates[i] || ''}"
              ></div>
            {/each}
          </div>
        {/each}
      </div>
    </div>
  {/each}

  <!-- legend -->
  <div class="hm-legend">
    <span class="hm-legend-text">less</span>
    {#each [0, 0.25, 0.5, 0.75, 1] as v}
      <div class="hm-legend-cell" style:background={cellColor(v, '#60a5fa')}></div>
    {/each}
    <span class="hm-legend-text">more</span>
  </div>
</div>

<style>
  .hm { display: flex; flex-direction: column; gap: var(--s-2); }
  .hm-row { display: flex; align-items: center; gap: var(--s-3); }
  .hm-label {
    display: flex; align-items: center; gap: 5px;
    width: 90px; flex-shrink: 0;
    font-size: 0.72rem; color: var(--text-dim); text-transform: capitalize;
  }
  .hm-dot { width: 8px; height: 8px; border-radius: 2px; flex-shrink: 0; }
  .hm-grid { display: flex; gap: 3px; overflow-x: auto; scrollbar-width: thin; }
  .hm-week { display: flex; flex-direction: column; gap: 3px; }
  .hm-cell { width: 14px; height: 14px; border-radius: 3px; flex-shrink: 0; transition: transform 0.15s ease; }
  .hm-cell:hover { transform: scale(1.2); }

  .hm-legend { display: flex; align-items: center; gap: 3px; margin-top: var(--s-3); padding-left: 96px; }
  .hm-legend-text { font-size: 0.65rem; color: var(--text-faint); padding: 0 4px; }
  .hm-legend-cell { width: 12px; height: 12px; border-radius: 2px; }
</style>