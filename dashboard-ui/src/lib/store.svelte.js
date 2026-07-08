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

  loading = $state(true);
  syncing = $state(false);
  error = $state(null);
  lastSyncAt = $state(null);

  async loadAll() {
    this.loading = true;
    this.error = null;
    try {
      const [status, today, gaps, scoreHistory, heatmap, timeAllocation] = await Promise.all([
        api.status(),
        api.today(),
        api.gaps(),
        api.scoreHistory(14),
        api.heatmap(90),
        api.timeAllocation('today'),
      ]);
      this.status = status;
      this.today = today;
      this.gaps = gaps;
      this.scoreHistory = scoreHistory;
      this.heatmap = heatmap;
      this.timeAllocation = timeAllocation;
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

  // composite score for today (last entry in scoreHistory)
  get todayScore() {
    if (!this.scoreHistory.length) return 0;
    return this.scoreHistory[this.scoreHistory.length - 1].score;
  }

  get yesterdayScore() {
    if (this.scoreHistory.length < 2) return null;
    return this.scoreHistory[this.scoreHistory.length - 2].score;
  }

  get scoreDelta() {
    if (this.yesterdayScore === null) return null;
    return this.todayScore - this.yesterdayScore;
  }
}

export const store = new DashboardStore();
