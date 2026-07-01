import json
import subprocess
from datetime import datetime, timezone, timedelta
from typing import List, Dict

from .config import Config

IST = timezone(timedelta(hours=5, minutes=30))

class TogglFetcher:
    def __init__(self, token_path: str = None):
        if token_path is None:
            token_path = "/root/.hermes/credentials/toggl_token.txt"
        self.token = open(token_path).read().strip()
        self.auth = f"{self.token}:api_token"
        self.base = "https://api.track.toggl.com/api/v9"

    def _req(self, endpoint: str):
        url = f"{self.base}/{endpoint}"
        cmd = ["curl", "-s", "-u", self.auth, "-H", "Content-Type: application/json", url]
        out = subprocess.check_output(cmd)
        return json.loads(out)

    def fetch_all(self, since_days: int = 30) -> List[Dict]:
        # Fetch last N days of entries
        entries = self._req("me/time_entries?page=1")
        if isinstance(entries, dict) and "data" in entries:
            entries = entries["data"]
        return entries if isinstance(entries, list) else []

    def fetch_current(self) -> Dict:
        return self._req("me/time_entries/current")


class Categorizer:
    def __init__(self, config: Config = None):
        self.cfg = config or Config()
        self.goals = self.cfg.goals
        self.maint_kws = self.cfg.maintenance_keywords

    def is_maintenance(self, desc: str) -> bool:
        d = desc.lower()
        return any(kw in d for kw in self.maint_kws)

    def is_tax(self, desc: str) -> bool:
        d = desc.lower()
        return any(kw in d for kw in self.cfg.tax_keywords)

    def categorize(self, desc: str) -> List[str]:
        d = desc.lower()
        cats = []
        for name, goal in self.goals.items():
            for kw in goal.keywords:
                if kw in d:
                    cats.append(name)
                    break
        return cats

    def parse(self, raw_entries: List[Dict]) -> List[Dict]:
        parsed = []
        for e in raw_entries:
            start_iso = e.get("start")
            if not start_iso:
                continue
            start = self._to_ist(start_iso)
            dur = e.get("duration", 0)
            if dur < 0:
                dur = int((datetime.now(timezone.utc) - start.astimezone(timezone.utc)).total_seconds())
            desc = e.get("description", "")
            cats = self.categorize(desc)
            is_maint = self.is_maintenance(desc)
            is_tax = self.is_tax(desc)
            # Tax = no goal match AND not maintenance
            if not cats and not is_maint:
                is_tax = True
            parsed.append({
                "id": e.get("id"),
                "date": start.strftime("%Y-%m-%d"),
                "description": desc,
                "duration": dur,
                "categories": cats,
                "is_maintenance": is_maint,
                "is_tax": is_tax,
                "raw": e,
            })
        return parsed

    @staticmethod
    def _to_ist(iso_str: str) -> datetime:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        return dt.astimezone(IST)
