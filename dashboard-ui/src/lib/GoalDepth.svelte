<script>
  // Grouped bar chart — per-goal daily minutes over last 7 days.
  // 6 thin bars per day (one per goal), colored by goal color.
  // Clickable legend to highlight one goal. Hover shows tooltip.
  import { GOAL_COLORS } from "./colors.js";

  let { data = { dates: [], goals: {} } } = $props();

  let highlightedGoal = $state(null);

  let goalNames = $derived(Object.keys(data.goals ?? {}));
  let dates = $derived(data.dates ?? []);

  // ---- layout ----
  const W = 680, H = 200, padL = 36, padR = 16, padT = 20, padB = 28;
  let innerW = $derived(W - padL - padR);
  let innerH = $derived(H - padT - padB);

  // bar dimensions
  const BAR_W = 4;
  const BAR_GAP = 2;
  const GROUP_GAP = 12;
  let goalCount = $derived(goalNames.length);
  let groupWidth = $derived(goalCount * BAR_W + (goalCount - 1) * BAR_GAP);

  // compute max minutes for Y scale
  let maxMins = $derived.by(() => {
    let max = 0;
    for (const name of goalNames) {
      for (const m of data.goals[name] ?? []) {
        if (m > max) max = m;
      }
    }
    return Math.ceil(max / 10) * 10 || 50;
  });

  // nice Y ticks
  let yTicks = $derived.by(() => {
    const niceMax = maxMins;
    const ticks = [];
    const steps = 4;
    for (let i = 0; i <= steps; i++) {
      ticks.push(Math.round((niceMax * i) / steps));
    }
    return ticks;
  });

  // bar positions per day
  let dayGroups = $derived.by(() => {
    if (!dates.length) return [];
    const totalGroupWidth = groupWidth + GROUP_GAP;
    const totalNeeded = dates.length * totalGroupWidth;
    // scale to fit innerW
    const availPerDay = innerW / dates.length;
    const scale = Math.min(1, availPerDay / totalGroupWidth);
    const gw = groupWidth * scale;
    const gGap = GROUP_GAP * scale;
    const bw = BAR_W * scale;
    const bg = BAR_GAP * scale;

    return dates.map((date, di) => {
      const groupX = padL + di * (gw + gGap) + gGap / 2;
      const bars = goalNames.map((name, gi) => {
        const mins = data.goals[name]?.[di] ?? 0;
        const barH = (mins / maxMins) * innerH;
        return {
          name,
          mins,
          x: groupX + gi * (bw + bg),
          y: padT + innerH - barH,
          w: bw,
          h: barH,
          color: GOAL_COLORS[name] ?? "#60a5fa",
          highlighted: highlightedGoal === name,
          dimmed: highlightedGoal !== null && highlightedGoal !== name,
        };
      });
      return { date, groupX, bars, label: date.slice(5) };
    });
  });

  // ---- tooltip ----
  let tooltip = $state({ show: false, x: 0, y: 0, name: "", mins: 0, date: "" });

  function showTip(event, name, mins, date) {
    const wrap = event.currentTarget.closest(".gd-scroll");
    const rect = wrap.getBoundingClientRect();
    const barRect = event.currentTarget.getBoundingClientRect();
    tooltip = {
      show: true,
      x: barRect.left - rect.left + barRect.width / 2,
      y: barRect.top - rect.top - 4,
      name,
      mins,
      date,
    };
  }
  function hideTip() {
    tooltip = { ...tooltip, show: false };
  }

  function toggleGoal(name) {
    highlightedGoal = highlightedGoal === name ? null : name;
  }
</script>

<div class="gd">
  <!-- legend (clickable) -->
  <div class="gd-legend">
    {#each goalNames as name}
      <button
        class="gd-legend-btn"
        class:active={highlightedGoal === name}
        class:dimmed={highlightedGoal !== null && highlightedGoal !== name}
        onclick={() => toggleGoal(name)}
        aria-pressed={highlightedGoal === name}
      >
        <span class="gd-legend-dot" style="background: {GOAL_COLORS[name] ?? '#60a5fa'}"></span>
        <span class="gd-legend-name capitalize">{name}</span>
      </button>
    {/each}
  </div>

  <div class="gd-scroll" style="position: relative">
    <svg
      viewBox="0 0 {W} {H}"
      width="100%"
      height={H}
      role="img"
      aria-label="Per-goal daily minutes, last 7 days"
    >
      <!-- Y grid lines + labels -->
      {#each yTicks as t, i}
        {@const y = padT + innerH - (t / maxMins) * innerH}
        <line x1={padL} y1={y} x2={W - padR} y2={y} stroke="var(--surface-2)" stroke-width="1" />
        <text x={padL - 8} y={y + 3} text-anchor="end" class="gd-axis" fill="var(--text-faint)">{t}</text>
      {/each}

      <!-- bars + x labels -->
      {#each dayGroups as dg}
        <!-- x-axis label -->
        <text x={dg.groupX + groupWidth / 2} y={H - 8} text-anchor="middle" class="gd-axis" fill="var(--text-faint)">{dg.label}</text>

        {#each dg.bars as bar}
          <rect
            x={bar.x}
            y={bar.y}
            width={bar.w}
            height={Math.max(bar.h, bar.mins > 0 ? 1 : 0)}
            rx="1"
            fill={bar.color}
            opacity={bar.dimmed ? 0.25 : 1}
            class:gd-bar-highlighted={bar.highlighted}
            role="img"
            aria-label="{bar.name}: {bar.mins} minutes on {dg.date}"
            onmouseenter={(e) => showTip(e, bar.name, bar.mins, dg.date)}
            onmouseleave={hideTip}
          />
        {/each}
      {/each}
    </svg>

    <!-- tooltip -->
    {#if tooltip.show}
      <div class="gd-tooltip" style="left: {tooltip.x}px; top: {tooltip.y}px; transform: translate(-50%, -100%)">
        <div class="gd-tooltip-name capitalize">{tooltip.name}</div>
        <div class="gd-tooltip-val tabular">{tooltip.mins}m · {tooltip.date}</div>
      </div>
    {/if}
  </div>
</div>

<style>
  .gd { display: flex; flex-direction: column; gap: var(--s-3); }

  .gd-legend {
    display: flex;
    flex-wrap: wrap;
    gap: var(--s-1);
  }
  .gd-legend-btn {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    background: var(--surface-2);
    color: var(--text-dim);
    border: none;
    border-radius: var(--r-sm);
    padding: var(--s-1) var(--s-2);
    font: inherit;
    font-size: 0.72rem;
    font-weight: 600;
    cursor: pointer;
    min-height: 44px;
    transition: background 0.2s cubic-bezier(0.2, 0, 0, 1), color 0.2s cubic-bezier(0.2, 0, 0, 1), opacity 0.2s ease;
  }
  .gd-legend-btn:hover { background: var(--surface-3); }
  .gd-legend-btn.active {
    background: var(--surface-3);
    color: var(--text);
  }
  .gd-legend-btn.dimmed { opacity: 0.4; }
  .gd-legend-dot {
    width: 8px;
    height: 8px;
    border-radius: 2px;
    flex-shrink: 0;
  }
  .gd-legend-name { text-transform: capitalize; }

  .gd-scroll {
    overflow-x: auto;
    scrollbar-width: thin;
    position: relative;
  }
  svg { display: block; min-width: 340px; }

  .gd-axis {
    font-size: 9px;
    font-family: var(--font);
    font-variant-numeric: tabular-nums;
  }

  .gd-bar-highlighted {
    filter: drop-shadow(0 0 4px currentColor);
  }

  .gd-tooltip {
    position: absolute;
    background: var(--surface-3);
    border-radius: var(--r-sm);
    padding: var(--s-1) var(--s-2);
    box-shadow: var(--shadow-2);
    z-index: 10;
    pointer-events: none;
    white-space: nowrap;
  }
  .gd-tooltip-name {
    font-size: 0.68rem;
    font-weight: 700;
    color: var(--text);
  }
  .gd-tooltip-val {
    font-size: 0.65rem;
    color: var(--text-dim);
    font-variant-numeric: tabular-nums;
  }

  .capitalize { text-transform: capitalize; }

  @media (prefers-reduced-motion: reduce) {
    .gd-legend-btn { transition: none; }
  }
</style>