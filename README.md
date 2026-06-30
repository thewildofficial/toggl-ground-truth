# Ground Truth Goals

> Automatic goal tracking from Toggl time entries. No checkboxes. No self-deception. Time logged = progress.

## The Problem

You say you want to do mech interp research. You say you want to learn Arabic. But your **stated preferences** are disconnected from **ground truth**. You have Duolingo streaks because Duolingo *forces* you to log time. What about the goals that actually matter?

This system closes the gap by treating Toggl time entries as the single source of truth.

## How It Works

1. **Track time in Toggl** with descriptive entries (e.g., "mech interp research", "Duolingo Arabic", "meditate")
2. **Configure goals** in `config/goals.yaml` — target minutes + matching keywords per goal
3. **Run `python -m toggl_goals`** — fetches Toggl data, categorizes, computes streaks, persists to SQLite
4. **View the dashboard** — Flask web UI with today's board, streaks, gap forecast, heatmaps, reality checks

No manual checkboxes. If you didn't log time, the streak breaks. Brutal but fair.

## Quick Start

```bash
# Clone & setup
git clone <repo>
cd toggl-goals
pip install -r requirements.txt

# Configure your Toggl token
echo "YOUR_TOKEN" > ~/.toggl_token
# Or set TOGGL_API_TOKEN env var

# Configure goals in config/goals.yaml, then:
python -m toggl_goals          # sync + print report
python run.py web              # start dashboard on :5000
```

## Goal Tiers

| Tier | Meaning | Examples |
|---|---|---|
| **non-negotiable** | Daily habit, streak-or-die | meditation, language |
| **high-ideal** | Stated life priorities | research, learning |
| **foundation** | Enabling infrastructure | fitness |

Maintenance work (exam prep, school assignments) is tracked separately so it can't subsidize your high-ideal scores.

## Architecture

```
toggl_goals/
  config.py          # YAML config loader
  toggl.py           # Toggl API fetch + categorization
  engine.py          # Streak computation, gap forecasting
  store.py           # SQLite persistence
  cli.py             # Command-line report

web/
  app.py             # Flask dashboard
  templates/
    dashboard.html   # Single-page app, no build step

config/
  goals.yaml         # Your stated preferences
```

## Philosophy

- **No self-reporting**: If it's not in Toggl, it didn't happen
- **Streaks over todo lists**: Todo lists measure *intention*. Streaks measure *behavior*.
- **Maintenance is not progress**: Exam prep is necessary but it doesn't count as research
- **Gap forecasting**: Shows how long to close the deficit at current pace. "never" = brutal wake-up call

## License

MIT
