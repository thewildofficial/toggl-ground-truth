import json
import os
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict

from flask import Flask, render_template, jsonify, request, send_from_directory
from flask_basicauth import BasicAuth

from toggl_goals.config import Config
from toggl_goals.store import Store
from toggl_goals.engine import StreakEngine, Report

app = Flask(__name__, template_folder=str(Path(__file__).parent / "templates"))
app.config['BASIC_AUTH_USERNAME'] = os.environ.get('GTG_USER', 'aban')
app.config['BASIC_AUTH_PASSWORD'] = os.environ.get('GTG_PASS', 'groundtruth')
app.config['BASIC_AUTH_FORCE'] = True
basic_auth = BasicAuth(app)

# Serve the built Svelte dashboard (dashboard-ui/dist) as static assets.
DIST_DIR = Path(__file__).parent.parent / "dashboard-ui" / "dist"

@app.route('/assets/<path:filename>')
@basic_auth.required
def serve_assets(filename):
    return send_from_directory(str(DIST_DIR / 'assets'), filename)

@app.route('/favicon.svg')
def favicon():
    return send_from_directory(str(DIST_DIR), 'favicon.svg')

store = Store()
config = Config()
engine = StreakEngine(config)

@app.route("/")
def index():
    if DIST_DIR.exists():
        return send_from_directory(str(DIST_DIR), "index.html")
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

    if not entries:
        return jsonify({"message": "No entries yet"})

    dates = sorted(set(e["date"] for e in entries))
    daily, maintenance, tax = engine.build_daily(entries)
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
    tax_mins = tax.get(today_str, 0) / 60
    total_mins = sum(board[b]["actual"] for b in range(len(board)))

    return jsonify({
        "date": today_str,
        "goals": board,
        "maintenance_mins": round(maint_mins, 1),
        "tax_mins": round(tax_mins, 1),
        "total_tracked_mins": round(total_mins + maint_mins + tax_mins, 1),
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
    daily, maintenance, tax = engine.build_daily(entries)
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
    tax_total = sum(tax.get(d, 0) for d in recent)
    result["_maintenance"] = {
        "weekly_hours": round(maint_total / 3600, 1),
        "daily_avg_mins": round(maint_total / 7 / 60, 1),
    }
    result["_tax"] = {
        "weekly_hours": round(tax_total / 3600, 1),
        "daily_avg_mins": round(tax_total / 7 / 60, 1),
    }

    return jsonify(result)

@app.route("/api/sync", methods=["POST"])
def api_sync():
    from toggl_goals.sync import Syncer
    syncer = Syncer()
    result = syncer.sync()
    return jsonify(result)

@app.route("/api/current")
def current_timer():
    from toggl_goals.sync import Syncer
    syncer = Syncer()
    timer = syncer.get_current_timer()
    if not timer:
        return jsonify({"running": False})
    return jsonify({
        "running": True,
        "description": timer["description"],
        "duration_mins": timer["duration"] / 60 if timer["duration"] > 0 else 0,
        "categories": timer.get("categories", []),
        "is_maintenance": timer.get("is_maintenance", False),
    })

def _build_report():
    """Recompute streaks/report from raw entries."""
    from toggl_goals.toggl import Categorizer
    cat = Categorizer(config)
    conn = store._conn()
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
    if not entries:
        return None
    dates = sorted(set(e["date"] for e in entries))
    daily, maintenance, tax = engine.build_daily(entries)
    full_days = engine.make_day_range(dates[0], dates[-1])

    # Merge screen_time data into daily for minimize goals.
    # Pull screen_time for the full date range so historical EMA is accurate.
    screen_time_by_date = store.get_screen_time_range(full_days[0], full_days[-1])
    if screen_time_by_date:
        daily = engine.merge_screen_time(daily, screen_time_by_date)

    streaks = engine.compute_streaks(full_days, daily)
    report = Report(streaks, daily, maintenance, tax, full_days, config)
    return report

@app.route("/api/score-history")
def score_history():
    report = _build_report()
    if not report:
        return jsonify([])
    days = request.args.get("days", 14, type=int)
    return jsonify(report.score_history(days))

@app.route("/api/heatmap")
def heatmap():
    report = _build_report()
    if not report:
        return jsonify({})
    days = request.args.get("days", 90, type=int)
    return jsonify(report.heatmap(days))

@app.route("/api/gap-trajectory")
def gap_trajectory():
    report = _build_report()
    if not report:
        return jsonify({})
    goal = request.args.get("goal", "research")
    days = request.args.get("days", 14, type=int)
    return jsonify(report.gap_trajectory(goal, days))

@app.route("/api/time-allocation")
def time_allocation():
    report = _build_report()
    if not report:
        return jsonify({})
    date = request.args.get("date", report.today)
    return jsonify(report.time_allocation(date))

@app.route("/api/score-analytics")
def score_analytics():
    report = _build_report()
    if not report:
        return jsonify({})
    days = request.args.get("days", 14, type=int)
    scores = report.score_history(days)
    moving_avg = report.score_moving_avg(days)
    slope = report.score_slope(days)
    forecast = report.score_forecast(days)
    # Label like "+2.3/day" or "-1.7/day"
    slope_label = f"+{slope['slope']:.1f}/day" if slope["slope"] >= 0 else f"{slope['slope']:.1f}/day"
    return jsonify({
        "scores": scores,
        "moving_avg": moving_avg,
        "slope": slope,
        "forecast": forecast,
        "slope_label": slope_label,
    })

@app.route("/api/goal-depth")
def goal_depth():
    report = _build_report()
    if not report:
        return jsonify({})
    days = request.args.get("days", 7, type=int)
    return jsonify(report.goal_daily_minutes(days))

@app.route("/api/ema-scores")
def ema_scores():
    """Per-goal EMA score history (Loop formula). Returns {history: {goal: [...]}, today: {goal: {score, checkmark}}}."""
    report = _build_report()
    if not report:
        return jsonify({})
    return jsonify(report.ema_scores())

@app.route("/api/ema-composite")
def ema_composite():
    """Composite EMA score for all days. Uses Loop's EMA formula with tier weighting."""
    report = _build_report()
    if not report:
        return jsonify([])
    return jsonify(report.ema_composite())

@app.route("/api/ema-today")
def ema_today():
    """Today's EMA composite score + per-goal breakdown."""
    report = _build_report()
    if not report:
        return jsonify({"score": 0, "breakdown": {}})
    return jsonify(report.ema_today())

@app.route("/api/screen-time", methods=["GET", "POST"])
def screen_time():
    """GET: per-category daily screen time for last N days (?days=7).
    POST: log screen_time records. Accepts single {date, category, seconds, source?}
          or batch {entries: [{date, category, seconds, source}]} (from extension)."""
    if request.method == "POST":
        data = request.get_json(silent=True) or {}
        records = data.get("entries", [data]) if "entries" in data else [data]
        saved = []
        for rec in records:
            date = rec.get("date")
            category = rec.get("category")
            seconds = rec.get("seconds")
            source = rec.get("source", "extension")
            if not date or not category or seconds is None:
                return jsonify({"error": "Required fields: date, category, seconds"}), 400
            try:
                seconds = int(seconds)
            except (ValueError, TypeError):
                return jsonify({"error": "seconds must be an integer"}), 400
            if seconds < 0:
                return jsonify({"error": "seconds must be non-negative"}), 400
            store.log_screen_time(date, category, seconds, source)
            saved.append({"date": date, "category": category, "seconds": seconds, "source": source})
        return jsonify({"status": "ok", "saved": saved})
    days = request.args.get("days", 7, type=int)
    result = store.get_screen_time_days(days)
    return jsonify(result)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
