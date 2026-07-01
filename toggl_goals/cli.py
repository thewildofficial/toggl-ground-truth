#!/usr/bin/env python3
"""
CLI runner: sync toggl data, compute streaks, persist, print report.
Usage: python -m toggl_goals.cli
"""
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from toggl_goals.sync import Syncer
from toggl_goals.engine import Report


def run():
    print("⏳ Syncing Toggl data...")
    syncer = Syncer()
    result = syncer.sync()

    if result["status"] != "ok":
        print(f"Sync failed: {result}")
        sys.exit(1)

    print(f"✅ Synced {result['fetched']} entries ({result['new']} new). Period: {result['period']}")

    # Load from store for report
    days = syncer.store.get_all_days()
    if not days:
        print("No data to report.")
        sys.exit(0)

    # Recompute report from stored data
    from toggl_goals.toggl import Categorizer
    from toggl_goals.engine import StreakEngine
    cat = Categorizer(syncer.config)
    conn = syncer.store._conn()
    rows = conn.execute("SELECT date, description, duration, categories, is_maintenance, is_tax FROM entries ORDER BY date").fetchall()
    conn.close()

    entries = []
    for r in rows:
        entries.append({
            "date": r[0],
            "description": r[1],
            "duration": r[2],
            "categories": json.loads(r[3]) if r[3] else [],
            "is_maintenance": bool(r[4]),
            "is_tax": bool(r[5]) if r[5] is not None else False,
        })

    dates = sorted(set(e["date"] for e in entries))
    daily, maintenance, tax = syncer.engine.build_daily(entries)
    full_days = syncer.engine.make_day_range(dates[0], dates[-1])
    streaks = syncer.engine.compute_streaks(full_days, daily)

    report = Report(streaks, daily, maintenance, tax, full_days, syncer.config)

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

    # Tax line
    print(f"\n{'─' * 60}")
    print("💸 PRODUCTIVITY TAX")
    print("─" * 60)
    tax_stats = report.tax_stats()
    print(f"  Today: {tax_stats['today_mins']:.0f}m")
    print(f"  7d avg: {tax_stats['daily_avg_mins']:.0f}m/day ({tax_stats['weekly_hours']:.1f}h/week)")

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
