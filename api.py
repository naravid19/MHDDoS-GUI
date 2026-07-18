# api.py
from __future__ import annotations

import logging
from typing import Any
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from src.core.state_manager import state_manager, AttackStateSnapshot
from src.api.ws_manager import ws_manager
from src.worker.service import worker_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mhddos_gui.api")

app = FastAPI(title="MHDDoS-GUI API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class StartAttackRequest(BaseModel):
    target: str = Field(..., description="Target URL or IP")
    duration: int = Field(..., gt=0, le=86400, description="Duration in seconds")
    threads: int = Field(..., gt=0, le=10000, description="Number of threads")
    method: str = Field(default="GET", description="Attack method")
    rpc: int = Field(default=100, gt=0, le=10000, description="Requests per connection")
    task_id: str | None = Field(default=None, description="Optional Task ID (generated if not provided)")


class StopAttackRequest(BaseModel):
    task_id: str | None = Field(default=None, description="Task ID to stop, stops all if omitted")


class ApiResponse(BaseModel):
    status: str
    message: str
    data: dict[str, Any] | AttackStateSnapshot | None = None


@app.get("/api/status", response_model=AttackStateSnapshot)
async def get_status() -> AttackStateSnapshot:
    """Returns the current atomic state snapshot from StateManager."""
    return await state_manager.get_state()


async def _api_log_handler(line: str) -> None:
    """Broadcasts CLI log lines to connected WebSocket clients."""
    from src.api.ws_manager import ws_manager, WSMessage
    import json
    import re
    
    # Strip ANSI escape codes
    ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
    line = ansi_escape.sub("", line).strip()
    if not line:
        return

    if line.startswith("{") and line.endswith("}"):
        try:
            data = json.loads(line)
            msg_type = data.get("type", "log")
            if "level" not in data:
                log_level = "INFO"
                if any(err in line.upper() for err in ["ERROR", "FAIL", "EXCEPTION"]):
                    log_level = "ERROR"
                elif any(warn in line.upper() for warn in ["WARNING", "WARN"]):
                    log_level = "WARNING"
                elif any(succ in line.upper() for succ in ["SUCCESS", "SOLVED"]):
                    log_level = "SUCCESS"
                data["level"] = log_level
            await ws_manager.broadcast(WSMessage(
                type=msg_type,
                payload=data
            ))
            return
        except json.JSONDecodeError:
            pass

    log_level = "INFO"
    if any(err in line.upper() for err in ["ERROR", "FAIL", "EXCEPTION"]):
        log_level = "ERROR"
    elif any(warn in line.upper() for warn in ["WARNING", "WARN"]):
        log_level = "WARNING"
    elif any(succ in line.upper() for succ in ["SUCCESS", "SOLVED"]):
        log_level = "SUCCESS"

    await ws_manager.broadcast(WSMessage(
        type="log",
        payload={"level": log_level, "msg": line}
    ))


@app.post("/api/attack/start", response_model=ApiResponse)
async def start_attack(request: StartAttackRequest) -> ApiResponse:
    """Triggers worker service to spawn background MHDDoS process."""
    try:
        task_id = await worker_service.start_attack(
            target=request.target,
            duration=request.duration,
            threads=request.threads,
            method=request.method,
            rpc=request.rpc,
            log_callback=_api_log_handler,
            attack_id=request.task_id,
        )
        current_state = await state_manager.get_state()
        return ApiResponse(
            status="success",
            message=f"Attack {task_id} started successfully.",
            data=current_state,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.exception("Error starting attack")
        raise HTTPException(status_code=500, detail="Internal server error starting attack.")


@app.post("/api/attack/stop", response_model=ApiResponse)
async def stop_attack(request: StopAttackRequest | None = None) -> ApiResponse:
    """Terminates running attack process tree via worker service."""
    try:
        task_id = request.task_id if request else None
        await worker_service.stop_attack(task_id)
        current_state = await state_manager.get_state()
        message = f"Attack {task_id} stopped successfully." if task_id else "All attacks stopped successfully."
        return ApiResponse(
            status="success",
            message=message,
            data=current_state,
        )
    except Exception as exc:
        logger.exception("Error stopping attack")
        raise HTTPException(status_code=500, detail="Internal server error stopping attack.")


@app.get("/api/attack/status")
@app.post("/api/attack/status")
async def get_attack_status() -> dict[str, Any]:
    """Returns the current attack status and active tasks."""
    return {
        "status": "success",
        "active_tasks": worker_service.get_active_tasks()
    }



@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """WebSocket endpoint managed by WSConnectionManager."""
    await ws_manager.connect(websocket)
    try:
        while True:
            # Keep connection open and handle client-side ping/messages if any
            data = await websocket.receive_text()
            logger.debug(f"Received WS message from client: {data}")
    except WebSocketDisconnect:
        await ws_manager.disconnect(websocket)
    except Exception as exc:
        logger.warning(f"WebSocket error: {exc}")
        await ws_manager.disconnect(websocket)


# Mount static web directory for frontend GUI
app.mount("/", StaticFiles(directory="web", html=True), name="web")
