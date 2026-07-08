<script>
  // Compact today tiles — per-goal accent colors.
  import { goalColor, statusColor } from './colors.js';
  let { goals = [] } = $props();
</script>

<div class="tiles">
  {#each goals as g (g.name)}
    <div class="tile" class:met={g.met} style:--goal={goalColor(g.name)}>
      <div class="t-top">
        <span class="t-dot" style:background={goalColor(g.name)}></span>
        <span class="t-name">{g.name}</span>
        {#if g.streak > 0}<span class="t-streak">{g.streak}d 🔥</span>{/if}
      </div>
      <div class="t-val tabular">{g.actual}<span class="t-unit">m</span></div>
      <div class="t-track">
        <div class="t-fill" style:width="{Math.min(g.pct*100,100)}%" style:background={statusColor(g.pct, g.met)}></div>
      </div>
      <div class="t-target tabular">/ {g.target}m</div>
    </div>
  {/each}
</div>

<style>
  .tiles { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: var(--s-3); }
  .tile {
    background: var(--surface-2);
    border-radius: var(--r-md);
    padding: var(--s-3);
    box-shadow: 0 0 0 1px color-mix(in srgb, var(--goal) 8%, transparent);
  }
  .tile.met { box-shadow: 0 0 0 1px color-mix(in srgb, var(--green) 35%, transparent); }
  .t-top { display: flex; align-items: center; gap: 5px; margin-bottom: var(--s-1); }
  .t-dot { width: 7px; height: 7px; border-radius: 2px; flex-shrink: 0; }
  .t-name { font-size: 0.8rem; font-weight: 600; text-transform: capitalize; flex: 1; }
  .t-streak { font-size: 0.68rem; color: var(--text-dim); }
  .t-val { font-size: 1.5rem; font-weight: 700; letter-spacing: -0.02em; }
  .t-unit { font-size: 0.8rem; font-weight: 500; color: var(--text-dim); margin-left: 1px; }
  .t-track { height: 5px; background: var(--surface-3); border-radius: var(--r-pill); margin: var(--s-2) 0 var(--s-1); overflow: hidden; }
  .t-fill { height: 100%; border-radius: var(--r-pill); transition: width 0.5s cubic-bezier(0.2,0,0,1); }
  .t-target { font-size: 0.72rem; color: var(--text-dim); }
</style>