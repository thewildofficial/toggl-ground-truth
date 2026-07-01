import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

DB_PATH = Path(__file__).parent.parent / "data" / "toggl_goals.db"

def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS daily_scores (
            date TEXT PRIMARY KEY,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            scores TEXT NOT NULL,  -- JSON: {goal_name: seconds}
            maintenance_seconds INTEGER DEFAULT 0,
            tax_seconds INTEGER DEFAULT 0,
            total_tracked_seconds INTEGER DEFAULT 0,
            streaks TEXT NOT NULL  -- JSON: {goal_name: current_streak}
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            toggl_id INTEGER UNIQUE,
            date TEXT,
            description TEXT,
            duration INTEGER,
            categories TEXT,  -- JSON list
            is_maintenance INTEGER,
            is_tax INTEGER,
            raw_json TEXT
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_entries_date ON entries(date)
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS meta (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)
    # Migrate: add is_tax column if missing (from old versions)
    try:
        conn.execute("ALTER TABLE entries ADD COLUMN is_tax INTEGER")
    except sqlite3.OperationalError:
        pass
    try:
        conn.execute("ALTER TABLE daily_scores ADD COLUMN tax_seconds INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass
    conn.commit()
    conn.close()

class Store:
    def __init__(self, db_path: Path = DB_PATH):
        self.db = str(db_path)
        init_db()

    def _conn(self):
        return sqlite3.connect(self.db)

    def save_day(self, date: str, scores: Dict[str, int], maintenance: int, tax: int, total: int, streaks: Dict[str, int]):
        conn = self._conn()
        conn.execute("""
            INSERT INTO daily_scores (date, scores, maintenance_seconds, tax_seconds, total_tracked_seconds, streaks)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(date) DO UPDATE SET
                scores=excluded.scores,
                maintenance_seconds=excluded.maintenance_seconds,
                tax_seconds=excluded.tax_seconds,
                total_tracked_seconds=excluded.total_tracked_seconds,
                streaks=excluded.streaks,
                updated_at=CURRENT_TIMESTAMP
        """, (date, json.dumps(scores), maintenance, tax, total, json.dumps(streaks)))
        conn.commit()
        conn.close()

    def get_day(self, date: str) -> Optional[Dict]:
        conn = self._conn()
        row = conn.execute(
            "SELECT date, scores, maintenance_seconds, tax_seconds, total_tracked_seconds, streaks FROM daily_scores WHERE date = ?",
            (date,)
        ).fetchone()
        conn.close()
        if not row:
            return None
        return {
            "date": row[0],
            "scores": json.loads(row[1]),
            "maintenance": row[2],
            "tax": row[3],
            "total": row[4],
            "streaks": json.loads(row[5]),
        }

    def get_range(self, start: str, end: str) -> List[Dict]:
        conn = self._conn()
        rows = conn.execute(
            "SELECT date, scores, maintenance_seconds, tax_seconds, total_tracked_seconds, streaks FROM daily_scores WHERE date >= ? AND date <= ? ORDER BY date",
            (start, end)
        ).fetchall()
        conn.close()
        return [
            {
                "date": r[0],
                "scores": json.loads(r[1]),
                "maintenance": r[2],
                "tax": r[3],
                "total": r[4],
                "streaks": json.loads(r[5]),
            }
            for r in rows
        ]

    def get_all_days(self) -> List[Dict]:
        conn = self._conn()
        rows = conn.execute(
            "SELECT date, scores, maintenance_seconds, tax_seconds, total_tracked_seconds, streaks FROM daily_scores ORDER BY date"
        ).fetchall()
        conn.close()
        return [
            {
                "date": r[0],
                "scores": json.loads(r[1]),
                "maintenance": r[2],
                "tax": r[3],
                "total": r[4],
                "streaks": json.loads(r[5]),
            }
            for r in rows
        ]

    def save_entries(self, entries: List[Dict]):
        conn = self._conn()
        for e in entries:
            conn.execute("""
                INSERT OR IGNORE INTO entries (toggl_id, date, description, duration, categories, is_maintenance, is_tax, raw_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                e.get("id"),
                e.get("date"),
                e.get("description"),
                e.get("duration"),
                json.dumps(e.get("categories", [])),
                1 if e.get("is_maintenance") else 0,
                1 if e.get("is_tax") else 0,
                json.dumps(e.get("raw", {})),
            ))
        conn.commit()
        conn.close()

    def get_meta(self, key: str) -> Optional[str]:
        conn = self._conn()
        row = conn.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
        conn.close()
        return row[0] if row else None

    def set_meta(self, key: str, value: str):
        conn = self._conn()
        conn.execute("INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)", (key, value))
        conn.commit()
        conn.close()
