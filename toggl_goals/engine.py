from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import math

from .config import Config


class StreakEngine:
    def __init__(self, config: Config = None):
        self.cfg = config or Config()
        self.goals = self.cfg.goals

    def build_daily(self, entries: List[Dict]) -> Dict[str, Dict[str, int]]:
        """Map date -> {goal_name: seconds}."""
        daily = defaultdict(lambda: defaultdict(int))
        maintenance = defaultdict(int)
        tax = defaultdict(int)
        for e in entries:
            date = e["date"]
            for cat in e.get("categories", []):
                daily[date][cat] += e["duration"]
            if e.get("is_maintenance"):
                maintenance[date] += e["duration"]
            elif e.get("is_tax"):
                tax[date] += e["duration"]
        return dict(daily), dict(maintenance), dict(tax)

    def compute_streaks(self, full_days: List[str], daily: Dict[str, Dict[str, int]]) -> Dict[str, Dict]:
        streaks = {}
        for name, goal in self.goals.items():
            target_secs = goal.target_mins * 60
            streak = 0
            max_streak = 0
            gap_total = 0
            log = []
            for day in full_days:
                actual = daily.get(day, {}).get(name, 0)
                met = actual >= target_secs
                log.append({"date": day, "seconds": actual, "met": met})
                if met:
                    streak += 1
                    max_streak = max(max_streak, streak)
                else:
                    streak = 0
                if actual < target_secs:
                    gap_total += (target_secs - actual)
            streaks[name] = {
                "current": streak,
                "max": max_streak,
                "gap_hours": gap_total / 3600,
                "log": log,
            }
        return streaks

    def rolling_avg(self, full_days: List[str], daily: Dict, goal_name: str, days: int = 7) -> float:
        recent = full_days[-days:] if len(full_days) >= days else full_days
        total = sum(daily.get(day, {}).get(goal_name, 0) for day in recent)
        return (total / len(recent)) / 60 if recent else 0.0

    def forecast(self, avg_mins: float, gap_hours: float, target_mins: int) -> str:
        if avg_mins <= 0 or gap_hours <= 0:
            return "n/a"
        gap_mins = gap_hours * 60
        if avg_mins < target_mins * 0.3:
            return "never"
        days = math.ceil(gap_mins / avg_mins)
        return f"{days}d"

    def make_day_range(self, start: str, end: str) -> List[str]:
        s = datetime.strptime(start, "%Y-%m-%d").date()
        e = datetime.strptime(end, "%Y-%m-%d").date()
        days = []
        cur = s
        while cur <= e:
            days.append(cur.strftime("%Y-%m-%d"))
            cur += timedelta(days=1)
        return days


class Report:
    def __init__(self, streaks: Dict, daily: Dict, maintenance: Dict, tax: Dict, full_days: List[str], config: Config = None):
        self.streaks = streaks
        self.daily = daily
        self.maintenance = maintenance
        self.tax = tax
        self.full_days = full_days
        self.cfg = config or Config()
        self.engine = StreakEngine(self.cfg)
        self.today = full_days[-1] if full_days else None

    def today_board(self) -> List[Dict]:
        rows = []
        for name, goal in self.cfg.goals.items():
            log = self.streaks[name]["log"]
            today_entry = next((l for l in log if l["date"] == self.today), None)
            secs = today_entry["seconds"] if today_entry else 0
            mins = secs / 60
            met = mins >= goal.target_mins
            streak = self.streaks[name]["current"]
            rows.append({
                "name": name,
                "icon": goal.icon,
                "color": goal.color,
                "tier": goal.tier,
                "target": goal.target_mins,
                "actual_mins": round(mins, 1),
                "met": met,
                "streak": streak,
            })
        return rows

    def gap_table(self) -> List[Dict]:
        rows = []
        for name, goal in self.cfg.goals.items():
            s = self.streaks[name]
            avg = self.engine.rolling_avg(self.full_days, self.daily, name, 7)
            catch = self.engine.forecast(avg, s["gap_hours"], goal.target_mins)
            rows.append({
                "name": name,
                "icon": goal.icon,
                "current": s["current"],
                "max": s["max"],
                "avg_mins": round(avg, 1),
                "gap_hours": round(s["gap_hours"], 1),
                "catch_up": catch,
            })
        return rows

    def maintenance_stats(self) -> Dict:
        recent = self.full_days[-7:]
        total = sum(self.maintenance.get(d, 0) for d in recent)
        avg_mins = (total / len(recent)) / 60 if recent else 0
        return {
            "weekly_hours": round(total / 3600, 1),
            "daily_avg_mins": round(avg_mins, 1),
        }

    def tax_stats(self) -> Dict:
        recent = self.full_days[-7:]
        total = sum(self.tax.get(d, 0) for d in recent)
        avg_mins = (total / len(recent)) / 60 if recent else 0
        today_secs = self.tax.get(self.today, 0)
        today_mins = today_secs / 60
        return {
            "weekly_hours": round(total / 3600, 1),
            "daily_avg_mins": round(avg_mins, 1),
            "today_mins": round(today_mins, 1),
        }

    def reality_check(self) -> List[Dict]:
        """Brutal truths."""
        truths = []
        research_avg = self.engine.rolling_avg(self.full_days, self.daily, "research", 7)
        research_target = self.cfg.goals["research"].target_mins
        maint = self.maintenance_stats()
        tax = self.tax_stats()

        if research_avg < research_target * 0.5:
            weekly_short = (research_target - research_avg) * 7 / 60
            truths.append({
                "severity": "brutal",
                "message": f"Research avg {research_avg:.0f}m/day vs {research_target}m target. Gap: {weekly_short:.1f}h/week.",
            })
        if maint["daily_avg_mins"] > 120:
            truths.append({
                "severity": "warning",
                "message": f"Maintenance burn {maint['daily_avg_mins']:.0f}m/day crowding out high-ideal work.",
            })
        if tax["daily_avg_mins"] > 60:
            truths.append({
                "severity": "warning",
                "message": f"Productivity tax {tax['daily_avg_mins']:.0f}m/day. Could fund {tax['daily_avg_mins']/30:.0f}x 30m goal blocks.",
            })
        return truths
