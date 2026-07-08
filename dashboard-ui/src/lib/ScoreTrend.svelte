<script>
  // Score trajectory — proper analytics chart with trendline, forecast, moving avg.
  // Hand-rolled SVG. No chart library. Ease-out cubic-bezier(0.2,0,0,1).
  // Computes movingAvg, slope, forecast internally if not provided as props.

  let {
    data = [],
    movingAvg = null,
    slope = null,
    forecast = null,
  } = $props();

  // ---- layout constants ----
  const W = 680, H = 240, padL = 40, padR = 20, padT = 24, padB = 32;

  // ---- log scale toggle ----
  let logScale = $state(false);

  // ---- compute analytics if not passed as props ----
  function computeMovingAvg(scores, window = 7) {
    return scores.map((_, i) => {
      const start = Math.max(0, i - window + 1);
      const chunk = scores.slice(start, i + 1);
      const avg = chunk.reduce((a, b) => a + b, 0) / chunk.length;
      return Math.round(avg * 10) / 10;
    });
  }

  function computeSlope(scores) {
    const n = scores.length;
    if (n < 2) return { slope: 0, intercept: 0, r_squared: 0 };
    const xs = Array.from({ length: n }, (_, i) => i);
    const sumX = xs.reduce((a, b) => a + b, 0);
    const sumY = scores.reduce((a, b) => a + b, 0);
    const sumXY = xs.reduce((s, x, i) => s + x * scores[i], 0);
    const sumX2 = xs.reduce((s, x) => s + x * x, 0);
    const denom = n * sumX2 - sumX * sumX;
    if (denom === 0) return { slope: 0, intercept: Math.round(sumY / n * 10) / 10, r_squared: 0 };
    const sl = (n * sumXY - sumX * sumY) / denom;
    const icept = (sumY - sl * sumX) / n;
    const meanY = sumY / n;
    const ssTot = scores.reduce((s, y) => s + (y - meanY) ** 2, 0);
    const ssRes = xs.reduce((s, x, i) => s + (y => (y - (sl * x + icept)) ** 2)(scores[i]), 0);
    const r2 = ssTot !== 0 ? 1 - ssRes / ssTot : 0;
    return {
      slope: Math.round(sl * 100) / 100,
      intercept: Math.round(icept * 10) / 10,
      r_squared: Math.round(r2 * 1000) / 1000,
    };
  }

  function computeForecast(scores, slopeData, forecastDays = 7) {
    if (!scores.length) return [];
    const n = scores.length;
    const result = [];
    const lastDate = data[data.length - 1]?.date;
    if (!lastDate) return [];
    const lastD = new Date(lastDate);
    for (let f = 1; f <= forecastDays; f++) {
      const x = n - 1 + f;
      let projected = slopeData.slope * x + slopeData.intercept;
      projected = Math.max(0, Math.min(100, projected));
      const d = new Date(lastD);
      d.setDate(d.getDate() + f);
      const dateStr = d.toISOString().slice(0, 10);
      result.push({ date: dateStr, projected_score: Math.round(projected * 10) / 10 });
    }
    return result;
  }

  let scores = $derived(data.map((d) => d.score));
  let avgData = $derived(movingAvg ?? computeMovingAvg(scores));
  let slopeData = $derived(slope ?? computeSlope(scores));
  let forecastData = $derived(forecast ?? computeForecast(scores, slopeData));

  // ---- Y mapping (linear or log) ----
  function mapY(val, innerH, padT, useLog) {
    if (useLog) {
      const clamped = Math.max(1, val);
      return padT + innerH - (Math.log(clamped) / Math.log(100)) * innerH;
    }
    return padT + innerH - (val / 100) * innerH;
  }

  let innerW = $derived(W - padL - padR);
  let innerH = $derived(H - padT - padB);

  // Total span includes forecast dates
  let totalPoints = $derived(data.length + forecastData.length);
  let w = $derived(Math.max(W, totalPoints * 32));

  let innerW2 = $derived(w - padL - padR);

  // ---- raw line points ----
  let rawPoints = $derived.by(() => {
    if (!data.length) return [];
    const step = data.length > 1 ? innerW2 / (totalPoints - 1) : 0;
    return data.map((d, i) => ({
      x: padL + i * step,
      y: mapY(d.score, innerH, padT, logScale),
      score: d.score,
      date: d.date,
    }));
  });

  let rawLine = $derived(
    rawPoints.map((p, i) => `${i === 0 ? "M" : "L"}${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(" ")
  );
  let rawArea = $derived(
    rawPoints.length
      ? `${rawLine} L${rawPoints[rawPoints.length - 1].x.toFixed(1)},${padT + innerH} L${rawPoints[0].x.toFixed(1)},${padT + innerH} Z`
      : ""
  );

  // ---- moving avg points (smoothed via cardinal spline approximation) ----
  let avgPoints = $derived.by(() => {
    if (!data.length || !avgData.length) return [];
    const step = data.length > 1 ? innerW2 / (totalPoints - 1) : 0;
    return data.map((d, i) => ({
      x: padL + i * step,
      y: mapY(avgData[i] ?? d.score, innerH, padT, logScale),
      avg: avgData[i],
      date: d.date,
    }));
  });

  // smooth path using quadratic bezier between midpoints
  let avgLine = $derived.by(() => {
    if (avgPoints.length < 2) return "";
    let path = `M${avgPoints[0].x.toFixed(1)},${avgPoints[0].y.toFixed(1)}`;
    for (let i = 1; i < avgPoints.length; i++) {
      const prev = avgPoints[i - 1];
      const curr = avgPoints[i];
      const mx = (prev.x + curr.x) / 2;
      const my = (prev.y + curr.y) / 2;
      path += ` Q${prev.x.toFixed(1)},${prev.y.toFixed(1)} ${mx.toFixed(1)},${my.toFixed(1)}`;
    }
    const last = avgPoints[avgPoints.length - 1];
    path += ` L${last.x.toFixed(1)},${last.y.toFixed(1)}`;
    return path;
  });

  // ---- trendline (dashed, extends to right edge) ----
  let trendLine = $derived.by(() => {
    if (!data.length) return null;
    const n = data.length;
    const step = n > 1 ? innerW2 / (totalPoints - 1) : 0;
    const x0 = padL;
    const x1 = padL + (n - 1) * step;
    const y0 = mapY(slopeData.intercept, innerH, padT, logScale);
    const y1 = mapY(slopeData.slope * (n - 1) + slopeData.intercept, innerH, padT, logScale);
    // extend to right edge of chart
    const xEnd = padL + innerW2;
    const yEnd = mapY(slopeData.slope * (totalPoints - 1) + slopeData.intercept, innerH, padT, logScale);
    return { x0, y0, x1, y1, xEnd, yEnd };
  });

  // ---- forecast line + confidence band ----
  let forecastPoints = $derived.by(() => {
    if (!data.length || !forecastData.length) return [];
    const step = data.length > 1 ? innerW2 / (totalPoints - 1) : 0;
    const n = data.length;
    const result = [];
    for (let i = 0; i < forecastData.length; i++) {
      const idx = n + i;
      const x = padL + idx * step;
      const y = mapY(forecastData[i].projected_score, innerH, padT, logScale);
      // confidence band widens with distance
      const bandWidth = (i + 1) * (innerH * 0.04);
      result.push({
        x,
        y,
        yUpper: Math.max(padT, y - bandWidth),
        yLower: Math.min(padT + innerH, y + bandWidth),
        projected: forecastData[i].projected_score,
        date: forecastData[i].date,
      });
    }
    return result;
  });

  let forecastLine = $derived(
    forecastPoints.length
      ? (() => {
          const lastRaw = rawPoints[rawPoints.length - 1];
          let path = `M${lastRaw.x.toFixed(1)},${lastRaw.y.toFixed(1)}`;
          for (const p of forecastPoints) {
            path += ` L${p.x.toFixed(1)},${p.y.toFixed(1)}`;
          }
          return path;
        })()
      : ""
  );

  let forecastBand = $derived(
    forecastPoints.length
      ? (() => {
          const lastRaw = rawPoints[rawPoints.length - 1];
          let path = `M${lastRaw.x.toFixed(1)},${lastRaw.y.toFixed(1)}`;
          for (const p of forecastPoints) {
            path += ` L${p.x.toFixed(1)},${p.yUpper.toFixed(1)}`;
          }
          for (let i = forecastPoints.length - 1; i >= 0; i--) {
            path += ` L${forecastPoints[i].x.toFixed(1)},${forecastPoints[i].yLower.toFixed(1)}`;
          }
          path += ` L${lastRaw.x.toFixed(1)},${lastRaw.y.toFixed(1)} Z`;
          return path;
        })()
      : ""
  );

  // ---- grid ----
  let gridYs = $derived(
    [0, 25, 50, 75, 100].map((v) => ({
      y: mapY(v, innerH, padT, logScale),
      label: v,
    }))
  );

  // ---- x labels: 3-4 spread across ----
  let xLabels = $derived.by(() => {
    if (data.length < 2) return [];
    const count = Math.min(4, data.length);
    const idxs = [];
    for (let i = 0; i < count; i++) {
      idxs.push(Math.round((i * (data.length - 1)) / (count - 1)));
    }
    const step = innerW2 / (totalPoints - 1);
    return idxs.map((i) => ({
      x: padL + i * step,
      label: data[i].date.slice(5),
    }));
  });

  // ---- slope label ----
  let slopeLabel = $derived.by(() => {
    const s = slopeData.slope;
    const sign = s >= 0 ? "+" : "";
    const arrow = s >= 0 ? "▶" : "▼";
    return `${sign}${s.toFixed(1)}/day ${arrow}`;
  });

  let slopeColor = $derived(slopeData.slope >= 0 ? "var(--green)" : "var(--red)");
  let slopePos = $derived(trendLine ? { x: trendLine.x1 + 8, y: trendLine.y1 - 8 } : null);

  // ---- r² display ----
  let rSquaredPct = $derived(Math.round(slopeData.r_squared * 100));
</script>

<div class="chart-wrap">
  <div class="chart-header">
    <button
      class="log-toggle"
      class:active={logScale}
      onclick={() => (logScale = !logScale)}
      aria-pressed={logScale}
      aria-label="Toggle log scale Y-axis"
    >
      <svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true">
        <path
          d="M4 20V8M4 8h16M8 8v12M12 8v12M16 8v12M20 8v12"
          fill="none"
          stroke="currentColor"
          stroke-width="1.5"
          stroke-linecap="round"
        />
      </svg>
      <span>{logScale ? "Log" : "Linear"}</span>
    </button>
    {#if slopeData}
      <span class="r2" title="R² — how well the trendline fits the data">
        R² {rSquaredPct}%
      </span>
    {/if}
  </div>

  <div class="chart-scroll">
    <svg
      viewBox="0 0 {w} {H}"
      width="100%"
      height={H}
      role="img"
      aria-label="Score trend over {data.length} days with forecast"
    >
      <defs>
        <linearGradient id="stAreaGrad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="var(--accent)" stop-opacity="0.16" />
          <stop offset="100%" stop-color="var(--accent)" stop-opacity="0" />
        </linearGradient>
      </defs>

      <!-- grid lines -->
      {#each gridYs as g}
        <line
          x1={padL}
          y1={g.y}
          x2={w - padR}
          y2={g.y}
          stroke="var(--surface-2)"
          stroke-width="1"
        />
        <text
          x={padL - 8}
          y={g.y + 3}
          text-anchor="end"
          class="axis-label"
          fill="var(--text-faint)">{g.label}</text
        >
      {/each}

      <!-- x labels -->
      {#each xLabels as xl}
        <text
          x={xl.x}
          y={H - 8}
          text-anchor="middle"
          class="axis-label"
          fill="var(--text-faint)">{xl.label}</text
        >
      {/each}

      <!-- forecast confidence band -->
      {#if forecastBand}
        <path d={forecastBand} fill="var(--accent)" fill-opacity="0.08" />
      {/if}

      <!-- gradient area under raw line -->
      {#if rawArea}
        <path d={rawArea} fill="url(#stAreaGrad)" />
      {/if}

      <!-- trendline (dashed, extends to right edge) -->
      {#if trendLine}
        <line
          x1={trendLine.x0}
          y1={trendLine.y0}
          x2={trendLine.xEnd}
          y2={trendLine.yEnd}
          stroke="var(--yellow)"
          stroke-width="1.5"
          stroke-dasharray="6 4"
          opacity="0.7"
        />
      {/if}

      <!-- forecast line (dotted) -->
      {#if forecastLine}
        <path
          d={forecastLine}
          fill="none"
          stroke="var(--accent)"
          stroke-width="1.5"
          stroke-dasharray="2 3"
          opacity="0.6"
        />
      {/if}

      <!-- moving average line (thicker, smoothed, lighter accent) -->
      {#if avgLine}
        <path
          d={avgLine}
          fill="none"
          stroke="#93c5fd"
          stroke-width="3"
          stroke-linecap="round"
          stroke-linejoin="round"
          opacity="0.8"
        />
      {/if}

      <!-- raw score line (thin) -->
      {#if rawLine}
        <path
          d={rawLine}
          fill="none"
          stroke="var(--accent)"
          stroke-width="1.5"
          stroke-linecap="round"
          stroke-linejoin="round"
        />
      {/if}

      <!-- data points + labels -->
      {#each rawPoints as p, i}
        <circle
          cx={p.x}
          cy={p.y}
          r={i === rawPoints.length - 1 ? 4 : 2.5}
          fill={i === rawPoints.length - 1 ? "var(--accent)" : "var(--bg)"}
          stroke="var(--accent)"
          stroke-width={i === rawPoints.length - 1 ? 0 : 1.5}
        />
        {#if data.length <= 15}
          <text
            x={p.x}
            y={p.y - 8}
            text-anchor="middle"
            class="point-label"
            fill="var(--text)">{p.score}</text
          >
        {/if}
      {/each}

      <!-- forecast points -->
      {#each forecastPoints as p}
        <circle cx={p.x} cy={p.y} r="2" fill="var(--accent)" fill-opacity="0.5" />
      {/each}

      <!-- slope indicator label -->
      {#if slopePos}
        <text
          x={slopePos.x}
          y={slopePos.y}
          class="slope-label"
          fill={slopeColor}>{slopeLabel}</text
        >
      {/if}
    </svg>
  </div>
</div>

<style>
  .chart-wrap { display: flex; flex-direction: column; gap: var(--s-2); }
  .chart-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--s-3);
  }
  .log-toggle {
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
  .log-toggle:hover { background: var(--surface-3); }
  .log-toggle.active {
    background: color-mix(in srgb, var(--accent) 20%, var(--surface-2));
    color: var(--accent);
  }
  .r2 {
    font-size: 0.7rem;
    color: var(--text-faint);
    font-variant-numeric: tabular-nums;
  }
  .chart-scroll {
    overflow-x: auto;
    scrollbar-width: thin;
  }
  svg {
    display: block;
    min-width: 340px;
  }
  .axis-label {
    font-size: 9px;
    font-family: var(--font);
    font-variant-numeric: tabular-nums;
  }
  .point-label {
    font-size: 9px;
    font-weight: 700;
    font-variant-numeric: tabular-nums;
    font-family: var(--font);
  }
  .slope-label {
    font-size: 10px;
    font-weight: 700;
    font-variant-numeric: tabular-nums;
    font-family: var(--font);
  }

  @media (prefers-reduced-motion: reduce) {
    .log-toggle { transition: none; }
  }
</style>