#!/usr/bin/env python3
"""
CLI runner: fetch toggl data, compute streaks, persist, print report.
Usage: python -m toggl_goals.cli
"""
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add parent to path for local dev
sys.path.insert(0, str(Path(__file__).parent.parent))

from toggl_goals.config import Config
from toggl_goals.toggl import TogglFetcher, Categorizer
from toggl_goals.engine import StreakEngine, Report
from toggl_goals.store import Store


def run():
    print("⏳ Fetching Toggl data...")
    fetcher = TogglFetcher()
    raw = fetcher.fetch_all()
    if not raw:
        print("No entries found.")
        sys.exit(1)

    config = Config()
    cat = Categorizer(config)
    entries = cat.parse(raw)

    # Determine date range
    dates = sorted(set(e["date"] for e in entries))
    start, end = dates[0], dates[-1]

    engine = StreakEngine(config)
    daily, maintenance = engine.build_daily(entries)
    full_days = engine.make_day_range(start, end)
    streaks = engine.compute_streaks(full_days, daily)

    # Persist
    store = Store()
    for day in full_days:
        scores = daily.get(day, {})
        total = sum(scores.values())
        maint = maintenance.get(day, 0)
        day_streaks = {name: streaks[name]["current"] for name in streaks}
        store.save_day(day, scores, maint, total, day_streaks)
    store.save_entries(entries)
    store.set_meta("last_sync", datetime.now(timezone.utc).isoformat())

    # Report
    report = Report(streaks, daily, maintenance, full_days, config)

    print()
    print("═" * 60)
    print(" GROUND TRUTH GOALS — DAILY REPORT")
    print(f" {report.today}  |  {len(full_days)} days tracked")
    print("═" * 60)

    # Today board
    print("\n📍 TODAY'S SCOREBOARD")
    print("─" * 60)
    for row in report.today_board():
        status = "✅" if row["met"] else "❌"
        pct = min(row["actual_mins"] / row["target"], 1.0) if row["target"] > 0 else 0
        bar = "█" * int(pct * 10) + "░" * (10 - int(pct * 10))
        print(f"  {status} {row['icon']} {row['name']:14s} {row['actual_mins']:5.1f}/{row['target']:3d}m [{bar}]  🔥{row['streak']}d")

    # Streaks
    print(f"\n{'─' * 60}")
    print("🔥 STREAKS + GAP FORECAST")
    print("─" * 60)
    print(f"  {'goal':14s} {'streak':>8s} {'7d avg':>8s} {'gap':>8s} {'catch-up':>10s}")
    for row in report.gap_table():
        print(f"  {row['icon']} {row['name']:12s} {row['current']:3d}/{row['max']:2d}d  {row['avg_mins']:6.1f}m  {row['gap_hours']:6.1f}h  {row['catch_up']:>10s}")

    # Reality check
    truths = report.reality_check()
    if truths:
        print(f"\n{'─' * 60}")
        print("🎯 REALITY CHECK")
        print("─" * 60)
        for t in truths:
            emoji = "🥀" if t["severity"] == "brutal" else "⚠️"
            print(f"  {emoji} {t['message']}")

    maint = report.maintenance_stats()
    print(f"\n  Maintenance burn: {maint['daily_avg_mins']:.0f}m/day ({maint['weekly_hours']:.1f}h/week)")
    print("═" * 60)


if __name__ == "__main__":
    run()
