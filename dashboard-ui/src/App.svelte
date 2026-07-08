<script>
  import { onMount } from 'svelte';
  import { store } from './lib/store.svelte.js';
  import Section from './lib/Section.svelte';
  import ScoreDonut from './lib/ScoreDonut.svelte';
  import ScoreTrend from './lib/ScoreTrend.svelte';
  import Heatmap from './lib/Heatmap.svelte';
  import TodayTiles from './lib/TodayTiles.svelte';

  onMount(() => store.loadAll());

  let todayGoals = $derived(store.today?.goals ?? []);
  let metCount = $derived(todayGoals.filter(g => g.met).length);
</script>

<header class="top">
  <div>
    <h1>Ground Truth</h1>
    <p class="tag">No checkboxes. Time logged = progress.</p>
  </div>
  <button class="sync" onclick={() => store.sync()} disabled={store.syncing} aria-label="Sync with Toggl">
    <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
      <path d="M21 12a9 9 0 1 1-3-6.7M21 4v4h-4" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>
    {store.syncing ? 'Syncing' : 'Sync'}
  </button>
</header>

{#if store.error}
  <p class="err">⚠ {store.error}</p>
{/if}

{#if store.loading}
  <p class="loading">Loading your truth…</p>
{:else}
  <!-- COMPACT DEFAULT VIEW: score + today at a glance -->
  <section class="hero">
    <ScoreDonut score={store.todayScore} delta={store.scoreDelta} />
    <div class="hero-side">
      <div class="hero-stat">
        <span class="hs-num tabular">{metCount}/{todayGoals.length}</span>
        <span class="hs-label">goals met today</span>
      </div>
      <div class="hero-stat">
        <span class="hs-num tabular">{store.status?.days_tracked ?? 0}</span>
        <span class="hs-label">days tracked</span>
      </div>
      <p class="sync-note">
        Last sync {store.status?.last_sync ? new Date(store.status.last_sync).toLocaleString() : 'never'}
      </p>
    </div>
  </section>

  <!-- EXPANDABLE SECTIONS -->
  <Section title="Today's Scoreboard" subtitle={metCount + " of " + todayGoals.length + " goals met"} badge={store.todayScore} defaultOpen={true}>
    <TodayTiles goals={todayGoals} />
  </Section>

  <Section title="Score Trajectory" subtitle="weighted composite, last 14 days" badge="{store.todayScore}%">
    <ScoreTrend data={store.scoreHistory} />
  </Section>

  <Section title="Streak Heatmap" subtitle="per-goal completion, last 90 days">
    {#if store.heatmap}<Heatmap heatmap={store.heatmap} />{/if}
  </Section>

  <Section title="Reality Check" subtitle="where stated ≠ ground truth">
    {#if store.gaps}
      {@const m = store.gaps._maintenance}
      {@const t = store.gaps._tax}
      <div class="truths">
        {#if m && m.daily_avg_mins > 120}
          <p class="truth warn">🔥 Maintenance burn {m.daily_avg_mins}m/day ({m.weekly_hours}h/wk) — crowding out ideal work.</p>
        {/if}
        {#if store.gaps.research && store.gaps.research.avg_mins < store.gaps.research.target * 0.5}
          {@const short = ((store.gaps.research.target - store.gaps.research.avg_mins) * 7 / 60).toFixed(1)}
          <p class="truth bad">🥀 Research {short}h/wk short of target. Stated priority ≠ logged time.</p>
        {/if}
        {#if t && t.daily_avg_mins > 60}
          <p class="truth warn">💸 Tax {t.daily_avg_mins}m/day. = {Math.round(t.daily_avg_mins/30)}x 30m blocks leaked.</p>
        {/if}
        {#if (!m || m.daily_avg_mins <= 120) && (!store.gaps.research || store.gaps.research.avg_mins >= store.gaps.research.target * 0.5) && (!t || t.daily_avg_mins <= 60)}
          <p class="truth good">✅ No gaps flagged. You are who you say you are.</p>
        {/if}
      </div>
    {/if}
  </Section>

  <Section title="Productivity Tax" subtitle="time not matching any goal">
    {#if store.gaps?._tax}
      {@const tax = store.gaps._tax}
      <div class="tax-grid">
        <div class="tax-cell"><span class="tc-num tabular">{store.today?.tax_mins ?? 0}m</span><span class="tc-label">today</span></div>
        <div class="tax-cell"><span class="tc-num tabular">{tax.daily_avg_mins}m</span><span class="tc-label">7d avg</span></div>
        <div class="tax-cell"><span class="tc-num tabular">{tax.weekly_hours}h</span><span class="tc-label">weekly</span></div>
      </div>
      <p class="tax-note">Tax = tracked time with no goal/maintenance match. The leak you're not looking at.</p>
    {/if}
  </Section>
{/if}

<style>
  .top { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: var(--s-5); }
  h1 { font-size: 1.5rem; letter-spacing: -0.03em; }
  .tag { font-size: 0.8rem; color: var(--text-dim); margin-top: 2px; }
  .sync {
    display: inline-flex; align-items: center; gap: var(--s-2);
    background: var(--surface-2); color: var(--text);
    border: none; border-radius: var(--r-pill);
    padding: var(--s-2) var(--s-4); font: inherit; font-size: 0.85rem; font-weight: 600;
    cursor: pointer; min-height: 44px;
    transition: background 0.2s cubic-bezier(0.2,0,0,1), transform 0.1s ease;
  }
  .sync:hover { background: var(--surface-3); }
  .sync:active { transform: scale(0.96); }
  .sync:disabled { opacity: 0.6; cursor: default; }

  .err { color: var(--red); font-size: 0.85rem; margin-bottom: var(--s-4); }
  .loading { color: var(--text-dim); padding: var(--s-6) 0; }

  .hero {
    display: flex; align-items: center; gap: var(--s-5);
    background: var(--surface-1); border-radius: var(--r-lg);
    padding: var(--s-5); margin-bottom: var(--s-4);
    box-shadow: var(--shadow-1);
  }
  .hero-side { display: flex; flex-direction: column; gap: var(--s-3); flex: 1; }
  .hero-stat { display: flex; flex-direction: column; }
  .hs-num { font-size: 1.8rem; font-weight: 700; letter-spacing: -0.02em; line-height: 1.1; }
  .hs-label { font-size: 0.75rem; color: var(--text-dim); text-transform: uppercase; letter-spacing: 0.04em; }
  .sync-note { font-size: 0.72rem; color: var(--text-faint); margin-top: auto; }

  .truths { display: flex; flex-direction: column; gap: var(--s-2); }
  .truth { font-size: 0.88rem; padding: var(--s-3); border-radius: var(--r-md); }
  .truth.bad { background: color-mix(in srgb, var(--red) 12%, transparent); color: var(--red); }
  .truth.warn { background: color-mix(in srgb, var(--yellow) 12%, transparent); color: var(--yellow); }
  .truth.good { background: color-mix(in srgb, var(--green) 12%, transparent); color: var(--green); }

  .tax-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: var(--s-3); margin-bottom: var(--s-3); }
  .tax-cell { background: var(--surface-2); border-radius: var(--r-md); padding: var(--s-3); text-align: center; }
  .tc-num { display: block; font-size: 1.4rem; font-weight: 700; color: var(--red); }
  .tc-label { font-size: 0.7rem; color: var(--text-dim); text-transform: uppercase; letter-spacing: 0.04em; }
  .tax-note { font-size: 0.78rem; color: var(--text-dim); }

  @media (max-width: 480px) {
    .hero { flex-direction: column; align-items: stretch; text-align: center; }
    .hero-side { align-items: center; }
    .sync-note { margin-top: var(--s-2); }
  }
</style>
