import sqlite3
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path


class Events:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self.connect()) as db, db:
            db.execute("""CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY, type TEXT NOT NULL, timestamp TEXT NOT NULL,
                source TEXT NOT NULL, people_in_roi INTEGER NOT NULL)""")
            db.execute("CREATE INDEX IF NOT EXISTS events_type_time ON events(type, timestamp)")

    def connect(self):
        db = sqlite3.connect(self.path)
        db.row_factory = sqlite3.Row
        return db

    def add(self, kind, source, count):
        now = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
        with closing(self.connect()) as db, db:
            db.execute("INSERT INTO events(type, timestamp, source, people_in_roi) VALUES (?, ?, ?, ?)",
                       (kind, now, source, count))

    def recent(self):
        with closing(self.connect()) as db:
            return [dict(row) for row in db.execute("SELECT * FROM events ORDER BY id DESC LIMIT 20")]

    def stats(self):
        hour = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
        buckets = {(hour - timedelta(hours=i)).isoformat()[:13]: 0 for i in range(23, -1, -1)}
        with closing(self.connect()) as db:
            total = db.execute("SELECT COUNT(*) FROM events WHERE type='ativacao'").fetchone()[0]
            rows = db.execute("""SELECT substr(timestamp, 1, 13) AS hour, COUNT(*) AS count
                FROM events WHERE type='ativacao' AND timestamp >= ? GROUP BY hour""",
                              (next(iter(buckets)),))
            for row in rows:
                if row["hour"] in buckets:
                    buckets[row["hour"]] = row["count"]
        return {"total": total, "hours": [{"time": key + ":00:00Z", "count": value}
                                        for key, value in buckets.items()]}
