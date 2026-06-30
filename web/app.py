import json
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict

from flask import Flask, render_template, jsonify

from toggl_goals.config import Config
from toggl_goals.store import Store
from toggl_goals.engine import StreakEngine

app = Flask(__name__, template_folder=str(Path(__file__).parent / "templates"))
store = Store()
config = Config()
engine = StreakEngine(config)

@app.route("/")
def index():
    return render_template("dashboard.html")

@app.route("/api/status")
def status():
    last_sync = store.get_meta("last_sync")
    days = store.get_all_days()
    return jsonify({
        "last_sync": last_sync,
        "days_tracked": len(days),
        "period": f"{days[0]['date']} → {days[-1]['date']}" if days else None,
    })

@app.route("/api/today")
def today():
    # Recompute from raw entries in DB for latest
    from toggl_goals.toggl import Categorizer
    cat = Categorizer(config)

    # Get entries from store
    conn = store._conn()
    rows = conn.execute("SELECT date, description, duration, categories, is_maintenance FROM entries ORDER BY date").fetchall()
    conn.close()

    entries = []
    for r in rows:
        entries.append({
            "date": r[0],
            "description": r[1],
            "duration": r[2],
            "categories": json.loads(r[3]) if r[3] else [],
            "is_maintenance": bool(r[4]),
        })

    if not entries:
        return jsonify({"message": "No entries yet"})

    dates = sorted(set(e["date"] for e in entries))
    daily, maintenance = engine.build_daily(entries)
    full_days = engine.make_day_range(dates[0], dates[-1])
    streaks = engine.compute_streaks(full_days, daily)
    today_str = full_days[-1]

    board = []
    for name, goal in config.goals.items():
        log = streaks[name]["log"]
        entry = next((l for l in log if l["date"] == today_str), None)
        secs = entry["seconds"] if entry else 0
        mins = secs / 60
        board.append({
            "name": name,
            "icon": goal.icon,
            "color": goal.color,
            "tier": goal.tier,
            "target": goal.target_mins,
            "actual": round(mins, 1),
            "met": mins >= goal.target_mins,
            "streak": streaks[name]["current"],
            "pct": min(mins / goal.target_mins, 1.0) if goal.target_mins > 0 else 0,
        })

    maint_mins = maintenance.get(today_str, 0) / 60
    total_mins = sum(board[b]["actual"] for b in range(len(board)))

    return jsonify({
        "date": today_str,
        "goals": board,
        "maintenance_mins": round(maint_mins, 1),
        "total_tracked_mins": round(total_mins + maint_mins, 1),
    })

@app.route("/api/history")
def history():
    days = store.get_all_days()
    if not days:
        return jsonify([])

    # Build per-goal heatmap data
    result = []
    for d in days:
        entry = {
            "date": d["date"],
            "scores": {},
            "streaks": d["streaks"],
            "maintenance": round(d["maintenance"] / 60, 1),
        }
        for name, secs in d["scores"].items():
            entry["scores"][name] = round(secs / 60, 1)
        result.append(entry)
    return jsonify(result)

@app.route("/api/gaps")
def gaps():
    days = store.get_all_days()
    if len(days) < 2:
        return jsonify({})

    # Recompute from raw entries
    from toggl_goals.toggl import Categorizer
    cat = Categorizer(config)

    conn = store._conn()
    rows = conn.execute("SELECT date, description, duration, categories, is_maintenance FROM entries ORDER BY date").fetchall()
    conn.close()

    entries = []
    for r in rows:
        entries.append({
            "date": r[0],
            "description": r[1],
            "duration": r[2],
            "categories": json.loads(r[3]) if r[3] else [],
            "is_maintenance": bool(r[4]),
        })

    dates = sorted(set(e["date"] for e in entries))
    daily, maintenance = engine.build_daily(entries)
    full_days = engine.make_day_range(dates[0], dates[-1])
    streaks = engine.compute_streaks(full_days, daily)

    result = {}
    for name, goal in config.goals.items():
        s = streaks[name]
        avg = engine.rolling_avg(full_days, daily, name, 7)
        catch = engine.forecast(avg, s["gap_hours"], goal.target_mins)
        result[name] = {
            "current_streak": s["current"],
            "max_streak": s["max"],
            "avg_mins": round(avg, 1),
            "gap_hours": round(s["gap_hours"], 1),
            "catch_up": catch,
            "target": goal.target_mins,
        }

    # Maintenance stats
    recent = full_days[-7:]
    maint_total = sum(maintenance.get(d, 0) for d in recent)
    result["_maintenance"] = {
        "weekly_hours": round(maint_total / 3600, 1),
        "daily_avg_mins": round(maint_total / 7 / 60, 1),
    }

    return jsonify(result)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
