"""SQLite storage for alerts and per-zone QoE snapshots. Plain functions over
sqlite3.Connection, no ORM -- stands in for Ovnicom's ClickHouse."""
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


def init_db(path: str = "sentinel.db") -> sqlite3.Connection:
    is_new = not Path(path).exists()
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row

    conn.execute("""
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_zone TEXT,
            client_id TEXT,
            qname TEXT,
            heuristic_kind TEXT,
            heuristic_score REAL,
            verdict TEXT,
            confidence REAL,
            reasoning TEXT,
            created_at TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS qoe_snapshots (
            zone TEXT PRIMARY KEY,
            avg_latency_ms REAL,
            nxdomain_rate REAL,
            qps REAL,
            score REAL,
            status TEXT,
            updated_at TEXT
        )
    """)
    conn.commit()
    _ = is_new  # nothing to seed for this domain, unlike Philips' taxonomy.csv
    return conn


def insert_alert(conn: sqlite3.Connection, event, candidate: dict, verdict: dict) -> int:
    cur = conn.execute(
        """INSERT INTO alerts
           (client_zone, client_id, qname, heuristic_kind, heuristic_score, verdict, confidence, reasoning, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            event.client_zone, event.client_id, event.qname, candidate["kind"], candidate["heuristic_score"],
            verdict["verdict"], verdict["confidence"], verdict["reasoning"],
            datetime.now(timezone.utc).isoformat(),
        ),
    )
    conn.commit()
    return cur.lastrowid


def get_recent_alerts(conn: sqlite3.Connection, limit: int = 50) -> list[dict]:
    rows = conn.execute("SELECT * FROM alerts ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return [dict(r) for r in rows]


def upsert_qoe(conn: sqlite3.Connection, zone: str, avg_latency_ms: float, nxdomain_rate: float, qps: float, score: float, status: str) -> None:
    conn.execute(
        """INSERT INTO qoe_snapshots (zone, avg_latency_ms, nxdomain_rate, qps, score, status, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)
           ON CONFLICT(zone) DO UPDATE SET
               avg_latency_ms = excluded.avg_latency_ms,
               nxdomain_rate = excluded.nxdomain_rate,
               qps = excluded.qps,
               score = excluded.score,
               status = excluded.status,
               updated_at = excluded.updated_at""",
        (zone, avg_latency_ms, nxdomain_rate, qps, score, status, datetime.now(timezone.utc).isoformat()),
    )
    conn.commit()


def get_all_qoe(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute("SELECT * FROM qoe_snapshots ORDER BY zone").fetchall()
    return [dict(r) for r in rows]
