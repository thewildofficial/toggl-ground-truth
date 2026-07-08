<script>
  // Compact today tiles. Click target wrapper handled by parent Section.
  let { goals = [] } = $props();

  function barColor(g) {
    if (g.met) return 'var(--green)';
    if (g.pct >= 0.5) return 'var(--yellow)';
    if (g.pct > 0) return 'var(--accent)';
    return 'var(--surface-3)';
  }
</script>

<div class="tiles">
  {#each goals as g (g.name)}
    <div class="tile" class:met={g.met}>
      <div class="t-top">
        <span class="t-name">{g.name}</span>
        {#if g.streak > 0}<span class="t-streak">{g.streak}d 🔥</span>{/if}
      </div>
      <div class="t-val tabular">{g.actual}<span class="t-unit">m</span></div>
      <div class="t-track"><div class="t-fill" style:width="{Math.min(g.pct*100,100)}%" style:background={barColor(g)}></div></div>
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
  }
  .tile.met { box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--green) 40%, transparent); }
  .t-top { display: flex; justify-content: space-between; align-items: baseline; margin-bottom: var(--s-1); }
  .t-name { font-size: 0.8rem; font-weight: 600; text-transform: capitalize; }
  .t-streak { font-size: 0.7rem; color: var(--text-dim); }
  .t-val { font-size: 1.5rem; font-weight: 700; letter-spacing: -0.02em; }
  .t-unit { font-size: 0.8rem; font-weight: 500; color: var(--text-dim); margin-left: 1px; }
  .t-track { height: 5px; background: var(--surface-3); border-radius: var(--r-pill); margin: var(--s-2) 0 var(--s-1); overflow: hidden; }
  .t-fill { height: 100%; border-radius: var(--r-pill); transition: width 0.5s cubic-bezier(0.2,0,0,1); }
  .t-target { font-size: 0.72rem; color: var(--text-dim); }
</style>
