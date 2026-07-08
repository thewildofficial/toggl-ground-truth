<script>
  // Per-goal heatmap — github-style density. ratio 0..1 → opacity ramp.
  let { heatmap } = $props();

  const COLS = 14; // weeks across
  function cells(goalCells) {
    // chunk into rows of COLS for vertical week layout
    const rows = [];
    for (let i = 0; i < goalCells.length; i += COLS) rows.push(goalCells.slice(i, i + COLS));
    return rows;
  }
  function ramp(ratio) {
    if (ratio <= 0) return 'var(--surface-3)';
    // accent at low opacity → full
    const a = 0.25 + ratio * 0.75;
    return `color-mix(in srgb, var(--accent) ${Math.round(a*100)}%, transparent)`;
  }
</script>

<div class="hm">
  {#each Object.entries(heatmap.goals) as [name, cellsArr]}
    <div class="hm-row">
      <span class="hm-label">{name}</span>
      <div class="hm-grid">
        {#each cells(cellsArr) as row}
          <div class="hm-week">
            {#each row as cell, i}
              <div class="hm-cell" style:background={ramp(cell)}
                   title="{name}: {Math.round(cell*100)}% on {heatmap.dates[i]}"></div>
            {/each}
          </div>
        {/each}
      </div>
    </div>
  {/each}
</div>

<style>
  .hm { display: flex; flex-direction: column; gap: var(--s-2); }
  .hm-row { display: flex; align-items: center; gap: var(--s-3); }
  .hm-label { width: 84px; font-size: 0.75rem; color: var(--text-dim); text-transform: capitalize; flex-shrink: 0; }
  .hm-grid { display: flex; gap: 3px; overflow-x: auto; }
  .hm-week { display: flex; flex-direction: column; gap: 3px; }
  .hm-cell { width: 11px; height: 11px; border-radius: 2px; flex-shrink: 0; }
</style>
