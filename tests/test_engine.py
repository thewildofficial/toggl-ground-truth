"""Regression tests for Ground Truth Goals engine.

Run:  pytest tests/test_engine.py -v
Or:   python -m pytest tests/test_engine.py
"""
import sys
from pathlib import Path

# Make the repo root importable when run from anywhere.
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from toggl_goals.config import Config
from toggl_goals.engine import StreakEngine, Report


def _make_config():
    """Minimal config with one maximize + one minimize goal (avoids YAML file)."""
    from toggl_goals.engine import StreakEngine  # noqa: F401 (ensure importable)
    cfg = Config()
    # Patch the raw backing store so cfg.goals picks up our synthetic goals.
    cfg._raw = {
        "goals": {
            "reading": {
                "target_mins": 30, "tier": "non-negotiable",
                "keywords": ["read", "reading"], "icon": "📖", "color": "#22c55e",
                "type": "maximize",
            },
            "doom_scroll": {
                "target_mins": 0, "tier": "non-negotiable",
                "keywords": ["doom", "scroll"], "icon": "🔥", "color": "#ef4444",
                "type": "minimize", "cap_mins": 30,
            },
        }
    }
    return cfg


def _days(n=5):
    from datetime import date, timedelta
    start = date(2026, 7, 1)
    return [(start + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(n)]


def test_minimize_streak_has_gap_hours_key():
    """THE REGRESSION: minimize goals must include 'gap_hours' in their
    streak dict, or gap_table() raises KeyError during the daily cron run."""
    cfg = _make_config()
    eng = StreakEngine(cfg)
    days = _days(5)
    # doom_scroll overshoots cap (30m) on 2 days: 60m + 90m over cap of 30m
    daily = {
        days[0]: {"doom_scroll": 60 * 60},   # 60m -> 30m over cap
        days[1]: {"doom_scroll": 90 * 60},   # 90m -> 60m over cap
    }
    streaks = eng.compute_streaks(days, daily)
    assert "gap_hours" in streaks["doom_scroll"], \
        "minimize goal missing 'gap_hours' -> gap_table() will KeyError"
    # 30m + 60m = 90m over cap = 1.5h
    assert abs(streaks["doom_scroll"]["gap_hours"] - 1.5) < 1e-9


def test_gap_table_runs_with_minimize_goals():
    """Full path that crashed in cron: Report.gap_table() must not raise
    when minimize goals are present."""
    cfg = _make_config()
    eng = StreakEngine(cfg)
    days = _days(5)
    daily = {
        days[0]: {"reading": 10 * 60, "doom_scroll": 45 * 60},
        days[1]: {"reading": 0, "doom_scroll": 10 * 60},
    }
    streaks = eng.compute_streaks(days, daily)
    report = Report(streaks, daily, {}, {}, days, cfg)
    rows = report.gap_table()  # previously KeyError: 'gap_hours'
    names = {r["name"] for r in rows}
    assert "doom_scroll" in names
    assert "reading" in names
    # every row must carry a numeric gap_hours (no missing key)
    for r in rows:
        assert isinstance(r["gap_hours"], (int, float))


def test_minimize_met_under_cap():
    """Under cap = streak continues, met=True."""
    cfg = _make_config()
    eng = StreakEngine(cfg)
    days = _days(3)
    daily = {d: {"doom_scroll": 10 * 60} for d in days}  # 10m < 30m cap
    streaks = eng.compute_streaks(days, daily)
    assert streaks["doom_scroll"]["current"] == 3
    assert streaks["doom_scroll"]["log"][-1]["met"] is True


def test_minimize_breaks_streak_over_cap():
    """Over cap resets streak, met=False."""
    cfg = _make_config()
    eng = StreakEngine(cfg)
    days = _days(3)
    daily = {
        days[0]: {"doom_scroll": 10 * 60},
        days[1]: {"doom_scroll": 90 * 60},  # over cap -> break
        days[2]: {"doom_scroll": 5 * 60},
    }
    streaks = eng.compute_streaks(days, daily)
    assert streaks["doom_scroll"]["current"] == 1  # only last day


def test_minimize_ema_inverted():
    """0 minutes -> checkmark 1.0; at cap -> checkmark 0.0."""
    cfg = _make_config()
    eng = StreakEngine(cfg)
    days = _days(2)
    daily = {days[0]: {"doom_scroll": 0}, days[1]: {"doom_scroll": 30 * 60}}
    scores = eng.compute_ema_scores(days, daily, "doom_scroll", goal=cfg.goals["doom_scroll"])
    assert scores[0]["checkmark"] == 1.0   # 0 mins, cap 30 -> 1.0
    assert scores[1]["checkmark"] == 0.0   # 30 mins, cap 30 -> 0.0
