import os
import sys
import asyncio
import subprocess
import re
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn
import tkinter as tk
from tkinter import filedialog

app = FastAPI(title="MHDDoS Professional API")

# --- Global State ---
attack_process = None
is_starting_attack = False
connected_websockets = []
ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

# --- Method Classifications ---
LAYER7 = ["BYPASS", "CFB", "GET", "POST", "OVH", "STRESS", "DYN", "SLOW", "HEAD",
          "NULL", "COOKIE", "PPS", "EVEN", "GSB", "DGB", "AVB", "CFBUAM",
          "APACHE", "XMLRPC", "BOT", "BOMB", "DOWNLOADER", "KILLER", "TOR", "RHEX", "STOMP"]

LAYER4_AMP = ["MEM", "NTP", "DNS", "ARD", "CLDAP", "CHAR", "RDP"]

LAYER4_NORMAL = ["TCP", "UDP", "SYN", "VSE", "MINECRAFT", "MCBOT", "CONNECTION", "CPS", 
                 "FIVEM", "FIVEM-TOKEN", "TS3", "MCPE", "ICMP", "OVH-UDP"]

PROXY_TYPES = {"All Proxy": "0", "HTTP": "1", "SOCKS4": "4", "SOCKS5": "5", "RANDOM": "6"}

class AttackParams(BaseModel):
    target: str
    method: str
    threads: str
    duration: str
    proxy_type: str = "SOCKS5"
    proxy_list: str = ""
    rpc: str = "100"
    reflector: str = ""

async def broadcast_log(message: str) -> None:
    """Sends a log message to all connected WebSockets"""
    for client in connected_websockets:
        try:
            await client.send_text(message)
        except Exception:
            pass

async def run_attack_subprocess(params: AttackParams) -> None:
    global attack_process, is_starting_attack
    
    # Pre-process Proxy List argument
    proxy_list_arg = params.proxy_list
    proxy_type_code = PROXY_TYPES.get(params.proxy_type, "5") # SOCKS5 as fallback
    
    if params.proxy_type == "All Proxy":
        if not proxy_list_arg:
            proxy_list_arg = "all.txt" # Default local file 
    
    if proxy_list_arg.startswith("http"):
        # If the user passed a URL, we pass that URL directly as the proxy list argument to start.py
        pass 
        
    command = [sys.executable, "-u", "start.py", params.method, params.target]
    
    if params.method in LAYER7:
        command.extend([proxy_type_code, params.threads, proxy_list_arg, params.rpc, params.duration])
    elif params.method in LAYER4_AMP:
        command.extend([params.threads, params.duration, params.reflector])
    elif params.method in LAYER4_NORMAL:
        if proxy_list_arg.strip() != "":
            command.extend([params.threads, params.duration, proxy_type_code, proxy_list_arg])
        else:
            command.extend([params.threads, params.duration])
            
    await broadcast_log(f"[*] Executing Command: {' '.join(command)}")

    try:
        attack_process = await asyncio.create_subprocess_exec(
            *command,
            cwd=os.path.dirname(os.path.abspath(__file__)),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT
        )
        is_starting_attack = False
        
        while True:
            line = await attack_process.stdout.readline()
            if not line:
                break
            # Decode carefully to handle any encoding quirks
            decoded_line = line.decode('utf-8', errors='replace').strip()
            
            # Remove ANSI color codes
            decoded_line = ansi_escape.sub('', decoded_line)
            
            if decoded_line:
                await broadcast_log(decoded_line)
                
        await attack_process.wait()
        await broadcast_log("[*] Attack process terminated gracefully.")
    except Exception as e:
        await broadcast_log(f"[!] Critical Error starting process: {e}")
        is_starting_attack = False
    finally:
        attack_process = None

@app.post("/api/attack/start")
async def start_attack(params: AttackParams) -> dict:
    global attack_process, is_starting_attack
    if attack_process is not None or is_starting_attack:
        return {"status": "error", "message": "An attack is already running."}
    
    is_starting_attack = True
    # Run the subprocess task in the background
    asyncio.create_task(run_attack_subprocess(params))
    return {"status": "success", "message": "Attack initiated."}

@app.post("/api/attack/stop")
async def stop_attack() -> dict:
    global attack_process
    if attack_process is None:
        return {"status": "error", "message": "No attack is currently running."}
    
    await broadcast_log("[!] Attempting to terminate the attack...")
    try:
        attack_process.terminate()
        return {"status": "success", "message": "Attack stopped."}
    except Exception as e:
        await broadcast_log(f"[!] Error attempting to stop process: {e}")
        return {"status": "error", "message": str(e)}

@app.get("/api/select_file")
async def select_file_dialog() -> dict:
    # Run tkinter in a separate thread to avoid blocking the async event loop
    def _open_dialog():
        root = tk.Tk()
        root.withdraw()
        root.wm_attributes('-topmost', 1)
        file_path = filedialog.askopenfilename(title="Select File", filetypes=(("Text Files", "*.txt"), ("All Files", "*.*")))
        root.destroy()
        return file_path
    
    loop = asyncio.get_event_loop()
    path = await loop.run_in_executor(None, _open_dialog)
    return {"path": path or ""}

@app.websocket("/ws/logs")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await websocket.accept()
    connected_websockets.append(websocket)
    try:
        while True:
            # We just keep connection open, client mainly receives
            await websocket.receive_text()
    except WebSocketDisconnect:
        connected_websockets.remove(websocket)

# Mount the web folder to serve HTML/CSS/JS (Stitch UI output)
app.mount("/", StaticFiles(directory="web", html=True), name="web")

def run():
    uvicorn.run("api:app", host="127.0.0.1", port=8000, log_level="info")

if __name__ == "__main__":
    run()
