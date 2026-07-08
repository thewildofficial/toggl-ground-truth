// Central reactive store (Svelte 5 runes in a .svelte.js module).
import { api } from './api.js';

class DashboardStore {
  // raw data
  status = $state(null);
  today = $state(null);
  gaps = $state(null);
  scoreHistory = $state([]);
  heatmap = $state(null);
  timeAllocation = $state(null);
  scoreAnalytics = $state(null);
  goalDepth = $state(null);
  emaToday = $state(null);        // EMA composite today {score, breakdown}
  emaComposite = $state([]);       // EMA composite history [{date, score, breakdown}]
  emaScores = $state(null);        // per-goal EMA {history, today}

  loading = $state(true);
  syncing = $state(false);
  error = $state(null);
  lastSyncAt = $state(null);

  async loadAll() {
    this.loading = true;
    this.error = null;
    try {
      const [status, today, gaps, scoreHistory, heatmap, timeAllocation, scoreAnalytics, goalDepth, emaToday, emaComposite, emaScores] = await Promise.all([
        api.status(),
        api.today(),
        api.gaps(),
        api.scoreHistory(14),
        api.heatmap(90),
        api.timeAllocation('today'),
        api.scoreAnalytics(14),
        api.goalDepth(7),
        api.emaToday(),
        api.emaComposite(),
        api.emaScores(),
      ]);
      this.status = status;
      this.today = today;
      this.gaps = gaps;
      this.scoreHistory = scoreHistory;
      this.heatmap = heatmap;
      this.timeAllocation = timeAllocation;
      this.scoreAnalytics = scoreAnalytics;
      this.goalDepth = goalDepth;
      this.emaToday = emaToday;
      this.emaComposite = emaComposite;
      this.emaScores = emaScores;
      this.lastSyncAt = new Date();
    } catch (e) {
      this.error = e.message;
    } finally {
      this.loading = false;
    }
  }

  async sync() {
    this.syncing = true;
    try {
      await api.sync();
      await this.loadAll();
    } catch (e) {
      this.error = e.message;
    } finally {
      this.syncing = false;
    }
  }

  // ---- derived helpers ----

  // EMA score for today (0-100)
  get todayScore() {
    return this.emaToday?.score ?? 0;
  }

  get yesterdayScore() {
    if (this.emaComposite.length < 2) return null;
    return this.emaComposite[this.emaComposite.length - 2].score;
  }

  get scoreDelta() {
    if (this.yesterdayScore === null) return null;
    return Math.round((this.todayScore - this.yesterdayScore) * 10) / 10;
  }

  get emaBreakdown() {
    return this.emaToday?.breakdown ?? null;
  }
}

export const store = new DashboardStore();