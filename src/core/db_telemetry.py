import sqlite3
import time
import logging
from pathlib import Path

DB_PATH = Path("data/telemetry.db")
logger = logging.getLogger(__name__)

_conn = None

def _get_conn():
    global _conn
    if _conn is None:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        _conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        _conn.row_factory = sqlite3.Row
    return _conn

def init_telemetry_db():
    conn = _get_conn()
    with conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS network_velocity (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp INTEGER,
                rps REAL,
                bps REAL
            )
        ''')
        # Index for fast timeframe querying
        conn.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON network_velocity(timestamp)')

def insert_telemetry_batch(rps: float, bps: float):
    now = int(time.time())
    try:
        conn = _get_conn()
        with conn:
            conn.execute(
                'INSERT INTO network_velocity (timestamp, rps, bps) VALUES (?, ?, ?)',
                (now, rps, bps)
            )
    except sqlite3.Error as e:
        logger.error(f"Telemetry DB Insert Error: {e}")

def get_telemetry_history(seconds: int) -> list[dict]:
    cutoff = int(time.time()) - seconds
    try:
        conn = _get_conn()
        cursor = conn.execute(
            'SELECT timestamp, rps, bps FROM network_velocity WHERE timestamp >= ? ORDER BY timestamp ASC',
            (cutoff,)
        )
        return [{"time": row["timestamp"] * 1000, "rps": row["rps"], "bps": row["bps"]} for row in cursor]
    except sqlite3.Error as e:
        logger.error(f"Telemetry DB Query Error: {e}")
        return []
