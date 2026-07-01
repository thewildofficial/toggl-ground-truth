import json
import subprocess
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional

from toggl_goals.store import Store
from toggl_goals.toggl import TogglFetcher, Categorizer
from toggl_goals.engine import StreakEngine
from toggl_goals.config import Config

IST = timezone(timedelta(hours=5, minutes=30))

class Syncer:
    def __init__(self, token_path: str = None):
        self.fetcher = TogglFetcher(token_path)
        self.cat = Categorizer()
        self.store = Store()
        self.config = Config()
        self.engine = StreakEngine(self.config)

    def sync(self, force_full: bool = False) -> Dict:
        """Fetch new toggl entries, store, recompute streaks."""
        # Try incremental: fetch since last sync
        last_sync = self.store.get_meta("last_sync")
        raw = self.fetcher.fetch_all()

        if not raw:
            return {"status": "no_data", "fetched": 0, "new": 0}

        entries = self.cat.parse(raw)
        if not entries:
            return {"status": "no_entries", "fetched": 0, "new": 0}

        # Check which toggl_ids we already have
        conn = self.store._conn()
        existing_ids = set(
            r[0] for r in conn.execute("SELECT toggl_id FROM entries WHERE toggl_id IS NOT NULL").fetchall()
        )
        conn.close()

        new_entries = [e for e in entries if e.get("id") and e["id"] not in existing_ids]

        # Save all (insert-or-ignore handles duplicates)
        self.store.save_entries(entries)

        # Recompute and save daily scores for all affected dates
        dates = sorted(set(e["date"] for e in entries))
        daily, maintenance, tax = self.engine.build_daily(entries)
        full_days = self.engine.make_day_range(dates[0], dates[-1])
        streaks = self.engine.compute_streaks(full_days, daily)

        for day in full_days:
            scores = daily.get(day, {})
            total = sum(scores.values())
            maint = maintenance.get(day, 0)
            t = tax.get(day, 0)
            day_streaks = {name: streaks[name]["current"] for name in streaks}
            self.store.save_day(day, scores, maint, t, total, day_streaks)

        self.store.set_meta("last_sync", datetime.now(timezone.utc).isoformat())

        return {
            "status": "ok",
            "fetched": len(entries),
            "new": len(new_entries),
            "period": f"{dates[0]} → {dates[-1]}",
        }

    def get_current_timer(self) -> Optional[Dict]:
        """Return currently running Toggl entry or None."""
        current = self.fetcher.fetch_current()
        if not current:
            return None
        return self.cat.parse([current])[0] if isinstance(current, dict) else None
