<script>
  // GitHub-style contribution heatmap — 7 rows (Mon-Sun) × N columns (weeks).
  // Per-goal tabs. Default "all" = composite (any goal met = green).
  // Cell coloring uses goal color, opacity by completion ratio.
  import { GOAL_COLORS } from "./colors.js";

  let { heatmap = { dates: [], goals: {} } } = $props();

  let activeTab = $state("all");

  // goal names derived from data
  let goalNames = $derived(Object.keys(heatmap.goals ?? {}));
  let dates = $derived(heatmap.dates ?? []);

  // build grid: 7 rows × N columns, aligned by weekday
  // determine start weekday so grid aligns properly
  let grid = $derived.by(() => {
    if (!dates.length) return { weeks: [], monthLabels: [] };

    // parse start date to find weekday offset
    const firstDate = new Date(dates[0] + "T00:00:00");
    const firstDow = firstDate.getDay(); // 0=Sun, 1=Mon...
    // convert to Monday-first: Mon=0, Tue=1, ... Sun=6
    const offset = firstDow === 0 ? 6 : firstDow - 1;

    // build cells array with nulls for padding before first date
    const cells = [];
    for (let i = 0; i < offset; i++) cells.push(null);
    for (let i = 0; i < dates.length; i++) cells.push(i);

    // chunk into weeks of 7
    const weeks = [];
    for (let i = 0; i < cells.length; i += 7) {
      weeks.push(cells.slice(i, i + 7));
    }
    // pad last week to 7
    const lastWeek = weeks[weeks.length - 1];
    if (lastWeek && lastWeek.length < 7) {
      while (lastWeek.length < 7) lastWeek.push(null);
    }

    // month labels: find first week that starts a new month
    const monthLabels = [];
    let lastMonth = -1;
    const monthNames = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
    for (let w = 0; w < weeks.length; w++) {
      // find first non-null cell in this week
      const firstCellIdx = weeks[w].findIndex((c) => c !== null);
      if (firstCellIdx === -1) {
        monthLabels.push(null);
        continue;
      }
      const dateIdx = weeks[w][firstCellIdx];
      const d = new Date(dates[dateIdx] + "T00:00:00");
      const m = d.getMonth();
      if (m !== lastMonth) {
        monthLabels.push(monthNames[m]);
        lastMonth = m;
      } else {
        monthLabels.push(null);
      }
    }

    return { weeks, monthLabels };
  });

  // get ratio for a cell index under active tab
  function getRatio(dateIdx) {
    if (dateIdx === null || dateIdx === undefined || dateIdx < 0) return null;
    if (activeTab === "all") {
      // composite: max ratio across goals (any goal met = green)
      let max = 0;
      for (const name of goalNames) {
        const r = heatmap.goals[name]?.[dateIdx] ?? 0;
        if (r > max) max = r;
      }
      return max;
    }
    return heatmap.goals[activeTab]?.[dateIdx] ?? 0;
  }

  function cellColor(ratio) {
    if (ratio === null || ratio <= 0) return "var(--surface-2)";
    const color = activeTab === "all" ? "#34d399" : GOAL_COLORS[activeTab] ?? "#60a5fa";
    const opacity = 0.2 + Math.min(ratio, 1) * 0.8;
    const alphaHex = Math.round(opacity * 255)
      .toString(16)
      .padStart(2, "0");
    return `${color}${alphaHex}`;
  }

  // ---- tooltip state ----
  let tooltip = $state({ show: false, x: 0, y: 0, date: "", ratios: [] });

  function showTip(event, dateIdx) {
    if (dateIdx === null || dateIdx === undefined) return;
    const date = dates[dateIdx];
    const ratios = goalNames.map((name) => ({
      name,
      ratio: heatmap.goals[name]?.[dateIdx] ?? 0,
      color: GOAL_COLORS[name] ?? "#60a5fa",
    }));
    const rect = event.currentTarget.closest(".hm-scroll").getBoundingClientRect();
    const cellRect = event.currentTarget.getBoundingClientRect();
    tooltip = {
      show: true,
      x: cellRect.left - rect.left + cellRect.width + 4,
      y: cellRect.top - rect.top,
      date,
      ratios,
    };
  }

  function hideTip() {
    tooltip = { ...tooltip, show: false };
  }

  // weekday labels: Mon, Wed, Fri (indices 0, 2, 4 in Monday-first)
  const weekdayLabels = [
    { label: "Mon", row: 0 },
    { label: "Wed", row: 2 },
    { label: "Fri", row: 4 },
  ];

  const CELL_SIZE = 14;
  const CELL_GAP = 3;
  const CELL_STEP = CELL_SIZE + CELL_GAP;

  // scale legend values
  const legendValues = [0, 0.25, 0.5, 0.75, 1];
</script>

<div class="hm">
  <!-- goal tabs -->
  <div class="hm-tabs">
    <button
      class="hm-tab"
      class:active={activeTab === "all"}
      onclick={() => (activeTab = "all")}
      aria-pressed={activeTab === "all"}
    >
      <span class="hm-tab-dot" style:background="#34d399"></span>
      All
    </button>
    {#each goalNames as name}
      <button
        class="hm-tab"
        class:active={activeTab === name}
        onclick={() => (activeTab = name)}
        aria-pressed={activeTab === name}
      >
        <span class="hm-tab-dot" style:background={GOAL_COLORS[name] ?? "#60a5fa"}></span>
        <span class="capitalize">{name}</span>
      </button>
    {/each}
  </div>

  <div class="hm-scroll" style="position: relative">
    <div class="hm-grid-wrap">
      <!-- month labels -->
      <div class="hm-months" style="padding-left: 32px">
        {#each grid.monthLabels as ml}
          <span class="hm-month-label" style="width: {CELL_STEP}px; flex-shrink: 0">
            {ml ?? ""}
          </span>
        {/each}
      </div>

      <div class="hm-body">
        <!-- weekday labels -->
        <div class="hm-weekdays">
          {#each weekdayLabels as wd}
            <span
              class="hm-wd-label"
              style="height: {CELL_STEP}px; line-height: {CELL_SIZE}px; top: {wd.row * CELL_STEP}px"
            >
              {wd.label}
            </span>
          {/each}
        </div>

        <!-- grid -->
        <div class="hm-grid">
          {#each grid.weeks as week, wIdx}
            <div class="hm-week" style="gap: {CELL_GAP}px">
              {#each week as dateIdx, dow}
                <div
                  class="hm-cell"
                  style="width: {CELL_SIZE}px; height: {CELL_SIZE}px; background: {cellColor(getRatio(dateIdx))}"
                  onmouseenter={(e) => showTip(e, dateIdx)}
                  onmouseleave={hideTip}
                  role="img"
                  aria-label={dateIdx !== null ? `${dates[dateIdx]}: ${Math.round(getRatio(dateIdx) * 100)}% complete` : "empty"}
                ></div>
              {/each}
            </div>
          {/each}
        </div>
      </div>

      <!-- scale legend -->
      <div class="hm-scale-legend">
        <span class="hm-legend-text">Less</span>
        {#each legendValues as v}
          <div
            class="hm-legend-cell"
            style="width: 12px; height: 12px; border-radius: 2px; background: {cellColor(v)}"
          ></div>
        {/each}
        <span class="hm-legend-text">More</span>
      </div>
    </div>

    <!-- tooltip -->
    {#if tooltip.show}
      <div
        class="hm-tooltip"
        style="left: {tooltip.x}px; top: {tooltip.y}px"
      >
        <div class="hm-tooltip-date">{tooltip.date}</div>
        {#each tooltip.ratios as r}
          <div class="hm-tooltip-row">
            <span class="hm-tooltip-dot" style:background={r.color}></span>
            <span class="hm-tooltip-name capitalize">{r.name}</span>
            <span class="hm-tooltip-val tabular">{Math.round(r.ratio * 100)}%</span>
          </div>
        {/each}
      </div>
    {/if}
  </div>
</div>

<style>
  .hm { display: flex; flex-direction: column; gap: var(--s-3); }

  .hm-tabs {
    display: flex;
    flex-wrap: wrap;
    gap: var(--s-1);
  }
  .hm-tab {
    display: inline-flex;
    align-items: center;
    gap: var(--s-1);
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
    transition: background 0.2s cubic-bezier(0.2, 0, 0, 1), color 0.2s cubic-bezier(0.2, 0, 0, 1);
  }
  .hm-tab:hover { background: var(--surface-3); }
  .hm-tab.active {
    background: var(--surface-3);
    color: var(--text);
  }
  .hm-tab-dot {
    width: 8px;
    height: 8px;
    border-radius: 2px;
    flex-shrink: 0;
  }

  .hm-scroll { overflow-x: auto; scrollbar-width: thin; position: relative; }
  .hm-grid-wrap { display: flex; flex-direction: column; gap: var(--s-2); min-width: max-content; padding-bottom: var(--s-2); }

  .hm-months {
    display: flex;
    gap: 3px;
    height: 16px;
  }
  .hm-month-label {
    font-size: 0.68rem;
    color: var(--text-faint);
    font-variant-numeric: tabular-nums;
  }

  .hm-body { display: flex; gap: var(--s-1); }
  .hm-weekdays {
    position: relative;
    width: 28px;
    flex-shrink: 0;
  }
  .hm-wd-label {
    position: absolute;
    left: 0;
    font-size: 0.68rem;
    color: var(--text-faint);
  }

  .hm-grid { display: flex; gap: 3px; }
  .hm-week { display: flex; flex-direction: column; }
  .hm-cell {
    border-radius: 3px;
    flex-shrink: 0;
    transition: transform 0.15s cubic-bezier(0.2, 0, 0, 1);
  }
  .hm-cell:hover {
    transform: scale(1.25);
    outline: 1px solid var(--text-dim);
  }

  .hm-scale-legend {
    display: flex;
    align-items: center;
    gap: 3px;
    align-self: flex-end;
    margin-top: var(--s-1);
  }
  .hm-legend-text {
    font-size: 0.65rem;
    color: var(--text-faint);
    padding: 0 4px;
  }

  .hm-tooltip {
    position: absolute;
    background: var(--surface-3);
    border-radius: var(--r-sm);
    padding: var(--s-2);
    box-shadow: var(--shadow-2);
    z-index: 10;
    pointer-events: none;
    min-width: 140px;
  }
  .hm-tooltip-date {
    font-size: 0.72rem;
    font-weight: 700;
    color: var(--text);
    margin-bottom: var(--s-1);
    font-variant-numeric: tabular-nums;
  }
  .hm-tooltip-row {
    display: flex;
    align-items: center;
    gap: 4px;
    font-size: 0.68rem;
  }
  .hm-tooltip-dot {
    width: 7px;
    height: 7px;
    border-radius: 2px;
    flex-shrink: 0;
  }
  .hm-tooltip-name { color: var(--text-dim); flex: 1; }
  .hm-tooltip-val { color: var(--text); font-weight: 600; }

  .capitalize { text-transform: capitalize; }

  @media (prefers-reduced-motion: reduce) {
    .hm-tab, .hm-cell { transition: none; }
    .hm-cell:hover { transform: none; }
  }
</style>