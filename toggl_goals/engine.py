from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import math

from .config import Config, Goal


class StreakEngine:
    def __init__(self, config: Config = None):
        self.cfg = config or Config()
        self.goals = self.cfg.goals

    def build_daily(self, entries: List[Dict]) -> Dict[str, Dict[str, int]]:
        """Map date -> {goal_name: seconds}.

        For maximize goals, only entries with matching goal keywords count.
        For minimize goals, both entries with matching goal keywords AND tax entries
        matching the minimize goal's keywords count (so doom-scrolling via Toggl
        tax entries drags the minimize goal down).
        """
        daily = defaultdict(lambda: defaultdict(int))
        maintenance = defaultdict(int)
        tax = defaultdict(int)
        minimize_goals = {n: g for n, g in self.goals.items() if g.is_minimize}
        for e in entries:
            date = e["date"]
            cats = e.get("categories", [])
            for cat in cats:
                daily[date][cat] += e["duration"]
            # Minimize goals also consume tax entries that match their keywords.
            # This makes the Toggl "tax" bucket (youtube, doom scroll, etc.) drag
            # down the corresponding minimize goal. Skip if already categorized
            # (cats non-empty) to avoid double counting.
            if e.get("is_tax") and not cats:
                desc = (e.get("description") or "").lower()
                for gname, goal in minimize_goals.items():
                    if any(kw in desc for kw in goal.keywords):
                        daily[date][gname] += e["duration"]
            if e.get("is_maintenance"):
                maintenance[date] += e["duration"]
            elif e.get("is_tax"):
                tax[date] += e["duration"]
        return dict(daily), dict(maintenance), dict(tax)

    def merge_screen_time(self, daily: Dict[str, Dict[str, int]], screen_time_by_date: Dict[str, Dict[str, int]]) -> Dict[str, Dict[str, int]]:
        """Merge screen_time data into the daily dict for minimize goals.

        screen_time_by_date: {date: {category: seconds}}
        Category names map to minimize goal names (e.g. "youtube" → youtube goal).
        Seconds are added on top of any Toggl-derived time for that goal/date.
        screen_time is stored in SECONDS; daily is also in SECONDS (EMA does /60).
        """
        minimize_goals = {n: g for n, g in self.goals.items() if g.is_minimize}
        # Build alias map: screen_time category -> minimize goal name
        alias_map = {}
        for gname, goal in minimize_goals.items():
            alias_map[gname] = gname
            alias_map[gname.replace("_", " ")] = gname
            for kw in goal.keywords:
                alias_map[kw] = gname
        result = {d: dict(v) for d, v in daily.items()}
        for date, cats in screen_time_by_date.items():
            for category, secs in cats.items():
                gname = alias_map.get(category) or alias_map.get(category.lower())
                if not gname:
                    norm = category.lower().replace(" ", "_")
                    gname = alias_map.get(norm)
                if gname:
                    result.setdefault(date, {})
                    result[date][gname] = result[date].get(gname, 0) + int(secs)
        return result

    def compute_streaks(self, full_days: List[str], daily: Dict[str, Dict[str, int]]) -> Dict[str, Dict]:
        streaks = {}
        for name, goal in self.goals.items():
            if goal.is_minimize:
                target_secs = goal.cap_mins * 60  # cap
                streak = 0
                max_streak = 0
                gap_total = 0
                log = []
                for day in full_days:
                    actual = daily.get(day, {}).get(name, 0)
                    met = actual <= target_secs  # minimize: under cap = good
                    log.append({"date": day, "seconds": actual, "met": met})
                    if met:
                        streak += 1
                        max_streak = max(max_streak, streak)
                    else:
                        streak = 0
                    if actual > target_secs:
                        gap_total += (actual - target_secs)
                streaks[name] = {
                    "current": streak,
                    "max": max_streak,
                    "gap_total": gap_total,
                    "log": log,
                    "type": "minimize",
                    "cap": goal.cap_mins,
                }
                continue
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

    # ---- Loop EMA Score Formula ----
    # Ported from uhabits-core/Score.kt
    # multiplier = 0.5 ^ (sqrt(frequency) / 13.0)
    # score = prevScore * multiplier + checkmarkValue * (1 - multiplier)
    # For daily goals (frequency=1.0): multiplier ≈ 0.9487
    # Each day: 5.13% toward today's value, 94.87% carry-forward
    # Misses decay gradually, don't reset to 0

    EMA_MULTIPLIER_DAILY = 0.5 ** (1.0 / 13.0)  # ≈ 0.9487 for frequency=1.0

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

    # ---- EMA scoring (ported from Loop Habit Tracker's Score.compute) ----
    # score = prevScore * multiplier + checkmarkValue * (1 - multiplier)
    # For daily goals (frequency=1.0): multiplier ≈ 0.9487
    # Each day: 5.13% toward today's value, 94.87% carry-forward
    # Misses decay gradually, don't reset to 0
    EMA_MULTIPLIER_DAILY = 0.5 ** (1.0 / 13.0)  # ≈ 0.9487 for frequency=1.0

    def compute_ema_scores(self, full_days: List[str], daily: Dict, goal_name: str, threshold_mins: int = None, goal: Goal = None) -> List[Dict]:
        """Per-goal EMA score history (0.0-1.0). Ported from Loop's Score.compute().

        For maximize goals: checkmark = min(1.0, minutes/target_mins)
        For minimize goals:  checkmark = max(0, 1 - minutes/cap_mins)
        """
        if goal is None:
            goal = self.goals.get(goal_name)
        if threshold_mins is None:
            threshold_mins = goal.threshold_mins if goal else 0
        is_minimize = bool(goal and goal.is_minimize)
        multiplier = self.EMA_MULTIPLIER_DAILY
        prev = 0.0
        scores = []
        for day in full_days:
            secs = daily.get(day, {}).get(goal_name, 0)
            mins = secs / 60
            if is_minimize:
                checkmark = max(0.0, 1.0 - mins / threshold_mins) if threshold_mins > 0 else 1.0
            else:
                checkmark = min(mins / threshold_mins, 1.0) if threshold_mins > 0 else 0.0
            prev = prev * multiplier + checkmark * (1 - multiplier)
            scores.append({"date": day, "score": round(prev * 100, 1), "checkmark": round(checkmark, 2)})
        return scores

    def compute_all_ema(self, full_days: List[str], daily: Dict) -> Dict[str, List[Dict]]:
        """EMA scores for all goals. Returns {goal_name: [{date, score, checkmark}, ...]}."""
        result = {}
        for name, goal in self.goals.items():
            result[name] = self.compute_ema_scores(full_days, daily, name, goal=goal)
        return result

    def composite_ema_score(self, full_days: List[str], daily: Dict) -> List[Dict]:
        """Weighted composite EMA score across all goals (0-100). Non-negotiables = 2x weight.

        Minimize goals are included with the same tier weighting; their checkmark is
        already inverted in compute_ema_scores, so a high score = little time spent.
        """
        TIER_WEIGHT = {"non-negotiable": 2.0, "high-ideal": 1.0, "foundation": 1.0}
        per_goal = {}
        for name, goal in self.cfg.goals.items():
            per_goal[name] = self.compute_ema_scores(full_days, daily, name, goal=goal)
        total_weight = sum(TIER_WEIGHT.get(g.tier, 1.0) for g in self.cfg.goals.values())
        composite = []
        for i, day in enumerate(full_days):
            weighted_sum = 0.0
            breakdown = {}
            for name, goal in self.cfg.goals.items():
                w = TIER_WEIGHT.get(goal.tier, 1.0)
                score_01 = per_goal[name][i]["score"] / 100 if i < len(per_goal[name]) else 0
                weighted_sum += score_01 * w
                breakdown[name] = round(score_01 * 100, 1)
            composite.append({
                "date": day,
                "score": round((weighted_sum / total_weight) * 100, 1) if total_weight else 0,
                "breakdown": breakdown,
            })
        return composite


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

    def composite_score(self, date: str) -> Dict:
        """Weighted daily score 0-100. Non-negotiable = 2x weight."""
        TIER_WEIGHT = {"non-negotiable": 2.0, "high-ideal": 1.0, "foundation": 1.0}
        total_weight = 0.0
        earned = 0.0
        breakdown = {}
        for name, goal in self.cfg.goals.items():
            w = TIER_WEIGHT.get(goal.tier, 1.0)
            secs = self.daily.get(date, {}).get(name, 0)
            mins = secs / 60
            ratio = min(mins / goal.target_mins, 1.0) if goal.target_mins > 0 else 0
            earned += ratio * w
            total_weight += w
            breakdown[name] = {
                "ratio": round(ratio, 2),
                "weight": w,
                "tier": goal.tier,
            }
        score = round((earned / total_weight) * 100) if total_weight else 0
        return {"date": date, "score": score, "breakdown": breakdown}

    def score_history(self, days: int = 14) -> List[Dict]:
        """Composite score for the last N days."""
        window = self.full_days[-days:] if days else self.full_days
        return [self.composite_score(d) for d in window]

    def heatmap(self, days: int = 90) -> Dict:
        """Per-goal daily completion ratio (0-1) for heatmap rendering."""
        window = self.full_days[-days:] if days else self.full_days
        result = {"dates": window, "goals": {}}
        for name, goal in self.cfg.goals.items():
            cells = []
            for d in window:
                secs = self.daily.get(d, {}).get(name, 0)
                mins = secs / 60
                ratio = min(mins / goal.target_mins, 1.0) if goal.target_mins > 0 else 0
                cells.append(round(ratio, 2))
            result["goals"][name] = cells
        return result

    def gap_trajectory(self, goal_name: str, days: int = 14) -> List[Dict]:
        """Daily gap_hours for a goal over the last N days (using running streak logic)."""
        if goal_name not in self.cfg.goals:
            return []
        window = self.full_days[-days:] if days else self.full_days
        log = self.streaks[goal_name]["log"]
        # map date -> gap at that point (cumulative)
        log_by_date = {l["date"]: l for l in log}
        traj = []
        for d in window:
            entry = log_by_date.get(d)
            # gap at this date = gap_hours if missed, else decay toward 0
            # approximate: use running cumulative from streaks
            gap = entry["gap_hours"] if entry else 0
            traj.append({"date": d, "gap_hours": round(gap, 1)})
        return traj

    def score_moving_avg(self, days: int = 14, window: int = 7) -> List[Dict]:
        """Rolling average of composite scores over `window` days."""
        history = self.score_history(days)
        result = []
        scores = [h["score"] for h in history]
        for i in range(len(history)):
            start = max(0, i - window + 1)
            chunk = scores[start:i + 1]
            avg = sum(chunk) / len(chunk) if chunk else 0
            result.append({"date": history[i]["date"], "avg": round(avg, 1)})
        return result

    def score_slope(self, days: int = 14) -> Dict:
        """Linear regression slope of composite scores. Returns {slope, intercept, r_squared}."""
        history = self.score_history(days)
        n = len(history)
        if n < 2:
            return {"slope": 0.0, "intercept": 0.0, "r_squared": 0.0}
        xs = list(range(n))
        ys = [h["score"] for h in history]
        sum_x = sum(xs)
        sum_y = sum(ys)
        sum_xy = sum(x * y for x, y in zip(xs, ys))
        sum_x2 = sum(x * x for x in xs)
        denom = n * sum_x2 - sum_x * sum_x
        if denom == 0:
            return {"slope": 0.0, "intercept": round(sum_y / n, 1), "r_squared": 0.0}
        slope = (n * sum_xy - sum_x * sum_y) / denom
        intercept = (sum_y - slope * sum_x) / n
        # r_squared
        mean_y = sum_y / n
        ss_tot = sum((y - mean_y) ** 2 for y in ys)
        ss_res = sum((y - (slope * x + intercept)) ** 2 for x, y in zip(xs, ys))
        r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0.0
        return {
            "slope": round(slope, 2),
            "intercept": round(intercept, 1),
            "r_squared": round(r_squared, 3),
        }

    def score_forecast(self, days: int = 14, forecast_days: int = 7) -> List[Dict]:
        """Extend the trendline forward by forecast_days days."""
        history = self.score_history(days)
        slope_data = self.score_slope(days)
        slope = slope_data["slope"]
        intercept = slope_data["intercept"]
        n = len(history)
        if n == 0:
            return []
        last_date_str = history[-1]["date"]
        last_date = datetime.strptime(last_date_str, "%Y-%m-%d").date()
        result = []
        for f in range(1, forecast_days + 1):
            x = n - 1 + f  # x continues from last history index
            projected = slope * x + intercept
            projected = max(0, min(100, projected))  # clamp 0-100
            forecast_date = (last_date + timedelta(days=f)).strftime("%Y-%m-%d")
            result.append({"date": forecast_date, "projected_score": round(projected, 1)})
        return result

    def goal_daily_minutes(self, days: int = 7) -> Dict:
        """Per-goal minutes per day for stacked/grouped bar chart."""
        window = self.full_days[-days:] if days else self.full_days
        goals = {}
        for name in self.cfg.goals:
            minutes = []
            for d in window:
                secs = self.daily.get(d, {}).get(name, 0)
                minutes.append(round(secs / 60, 1))
            goals[name] = minutes
        return {"dates": window, "goals": goals}

    def time_allocation(self, date: str) -> Dict:
        """Goal vs maintenance vs tax minutes for a day (stacked bar)."""
        goal_mins = sum(self.daily.get(date, {}).values()) / 60
        maint_mins = self.maintenance.get(date, 0) / 60
        tax_mins = self.tax.get(date, 0) / 60
        return {
            "date": date,
            "goal_mins": round(goal_mins, 1),
            "maintenance_mins": round(maint_mins, 1),
            "tax_mins": round(tax_mins, 1),
            "total_mins": round(goal_mins + maint_mins + tax_mins, 1),
        }

    # ---- EMA-based scores (Loop formula) ----

    def ema_scores(self) -> Dict:
        """Per-goal EMA score history + today's scores."""
        all_ema = self.engine.compute_all_ema(self.full_days, self.daily)
        today_scores = {}
        for name, hist in all_ema.items():
            today_scores[name] = hist[-1] if hist else {"date": self.today, "score": 0, "checkmark": 0}
        return {"history": all_ema, "today": today_scores}

    def ema_composite(self) -> List[Dict]:
        """Composite EMA score (0-100) with per-goal breakdown, for all days."""
        return self.engine.composite_ema_score(self.full_days, self.daily)

    def ema_today(self) -> Dict:
        """Today's EMA composite score + per-goal breakdown."""
        composite = self.ema_composite()
        if not composite:
            return {"score": 0, "breakdown": {}}
        today = composite[-1]
        return today
