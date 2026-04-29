import sqlite3
import os
import time

DB_PATH = "database/safewatch.db"

class DatabaseManager:
    def __init__(self):
        os.makedirs("database", exist_ok=True)
        self.db_path = DB_PATH
        self.init_db()

    def _connect(self):
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        conn = self._connect()
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS incidents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                camera_id TEXT NOT NULL,
                location TEXT NOT NULL,
                threat_type TEXT NOT NULL,
                threat_score REAL NOT NULL,
                woman_present INTEGER DEFAULT 1,
                status TEXT DEFAULT 'Monitoring',
                timestamp TEXT NOT NULL
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                camera_id TEXT NOT NULL,
                location TEXT NOT NULL,
                threat_type TEXT NOT NULL,
                threat_score REAL NOT NULL,
                snapshot_path TEXT,
                timestamp TEXT NOT NULL,
                resolved INTEGER DEFAULT 0,
                resolved_by TEXT,
                resolved_at TEXT
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS elevator_warnings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                camera_id TEXT NOT NULL,
                location TEXT NOT NULL,
                threat_type TEXT NOT NULL,
                timestamp TEXT NOT NULL
            )
        """)
        conn.commit()
        conn.close()
        print("  ✅ Database tables created successfully")

    def log_incident(self, camera_id, location, threat_type,
                     threat_score, woman_present=True, status="Monitoring"):
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        conn = self._connect()
        conn.execute(
            """INSERT INTO incidents
               (camera_id, location, threat_type, threat_score,
                woman_present, status, timestamp)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (camera_id, location, threat_type,
             round(threat_score, 3), int(woman_present), status, timestamp)
        )
        conn.commit()
        conn.close()

    def save_alert(self, camera_id, location, threat_type,
                   threat_score, snapshot_path, timestamp):
        conn = self._connect()
        conn.execute(
            """INSERT INTO alerts
               (camera_id, location, threat_type, threat_score,
                snapshot_path, timestamp)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (camera_id, location, threat_type,
             round(threat_score, 3), snapshot_path, timestamp)
        )
        conn.commit()
        conn.close()

    def save_elevator_warning(self, camera_id, location, threat_type):
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        conn = self._connect()
        conn.execute(
            """INSERT INTO elevator_warnings
               (camera_id, location, threat_type, timestamp)
               VALUES (?, ?, ?, ?)""",
            (camera_id, location, threat_type, timestamp)
        )
        conn.commit()
        conn.close()

    def resolve_alert(self, alert_id, resolved_by="Operator"):
        resolved_at = time.strftime("%Y-%m-%d %H:%M:%S")
        conn = self._connect()
        conn.execute(
            """UPDATE alerts SET resolved=1, resolved_by=?, resolved_at=?
               WHERE id=?""",
            (resolved_by, resolved_at, alert_id)
        )
        conn.commit()
        conn.close()

    def get_recent_alerts(self, limit=50, unresolved_only=False):
        conn = self._connect()
        if unresolved_only:
            rows = conn.execute(
                "SELECT * FROM alerts WHERE resolved=0 ORDER BY id DESC LIMIT ?",
                (limit,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM alerts ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_recent_incidents(self, limit=100):
        conn = self._connect()
        rows = conn.execute(
            "SELECT * FROM incidents ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_stats(self):
        conn = self._connect()
        total_alerts      = conn.execute("SELECT COUNT(*) FROM alerts").fetchone()[0]
        unresolved        = conn.execute("SELECT COUNT(*) FROM alerts WHERE resolved=0").fetchone()[0]
        total_incidents   = conn.execute("SELECT COUNT(*) FROM incidents").fetchone()[0]
        elevator_warnings = conn.execute("SELECT COUNT(*) FROM elevator_warnings").fetchone()[0]
        conn.close()
        return {
            "total_alerts":      total_alerts,
            "unresolved_alerts": unresolved,
            "total_incidents":   total_incidents,
            "elevator_warnings": elevator_warnings,
        }

    def get_alerts_by_location(self):
        conn = self._connect()
        rows = conn.execute(
            """SELECT location, COUNT(*) as count FROM alerts
               GROUP BY location ORDER BY count DESC"""
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]