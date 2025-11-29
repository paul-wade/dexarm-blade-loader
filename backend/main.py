"""
DexArm Blade Loader - FastAPI Backend
Provides REST API and WebSocket for real-time updates
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import asyncio
import threading

from dexarm_controller import DexArmController

app = FastAPI(title="DexArm Blade Loader API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global controller instance
controller = DexArmController()

# WebSocket connections for real-time updates
clients: list[WebSocket] = []


async def broadcast(message: dict):
    """Broadcast message to all connected clients"""
    for client in clients:
        try:
            await client.send_json(message)
        except:
            pass


def sync_broadcast(message: dict):
    """Sync wrapper for broadcasting from threads"""
    asyncio.run(broadcast(message))


# === Models ===

class ConnectRequest(BaseModel):
    port: str


class JogRequest(BaseModel):
    axis: str
    distance: float


class SettingsRequest(BaseModel):
    suction_grab_delay: Optional[float] = None
    suction_release_delay: Optional[float] = None
    feedrate: Optional[int] = None


# === Routes ===

@app.get("/api/ports")
def get_ports():
    """List available serial ports"""
    return {"ports": controller.list_ports()}


@app.get("/api/status")
def get_status():
    """Get current connection status and position"""
    return {
        "connected": controller.connected,
        "position": controller.current_pos,
        "is_running": controller.is_running,
        "is_paused": controller.pause_requested,
        "positions": controller.positions,
        "settings": controller.settings,
    }


@app.post("/api/connect")
def connect(req: ConnectRequest):
    """Connect to DexArm"""
    success, msg = controller.connect(req.port)
    if success:
        controller.set_module(2)
    return {"success": success, "message": msg}


@app.post("/api/disconnect")
def disconnect():
    """Disconnect from DexArm"""
    controller.disconnect()
    return {"success": True}


@app.post("/api/home")
def go_home():
    """Move to home position"""
    if not controller.connected:
        return {"success": False, "message": "Not connected"}
    controller.go_home()
    controller.get_position_from_encoder()
    return {"success": True, "position": controller.current_pos}


@app.post("/api/jog")
def jog(req: JogRequest):
    """Jog the arm"""
    if not controller.connected:
        return {"success": False, "message": "Not connected"}
    controller.jog(req.axis, req.distance)
    controller.get_position_from_encoder()
    return {"success": True, "position": controller.current_pos}


@app.post("/api/teach/enable")
def enable_teach_mode():
    """Enable free movement mode"""
    if not controller.connected:
        return {"success": False, "message": "Not connected"}
    controller.enable_teach_mode()
    return {"success": True}


@app.post("/api/teach/disable")
def disable_teach_mode():
    """Disable free movement mode"""
    if not controller.connected:
        return {"success": False, "message": "Not connected"}
    controller.get_position_from_encoder()
    controller.disable_teach_mode()
    return {"success": True, "position": controller.current_pos}


@app.post("/api/suction/grab")
def suction_grab():
    """Activate suction"""
    if not controller.connected:
        return {"success": False, "message": "Not connected"}
    controller.suction_grab()
    return {"success": True}


@app.post("/api/suction/release")
def suction_release():
    """Release suction"""
    if not controller.connected:
        return {"success": False, "message": "Not connected"}
    controller.suction_release()
    return {"success": True}


@app.post("/api/suction/off")
def suction_off():
    """Turn off suction"""
    if not controller.connected:
        return {"success": False, "message": "Not connected"}
    controller.suction_off()
    return {"success": True}


@app.post("/api/pick/set")
def set_pick():
    """Set current position as pick point"""
    if not controller.connected:
        return {"success": False, "message": "Not connected"}
    controller.set_pick()
    return {"success": True, "pick": controller.positions['pick']}


@app.post("/api/pick/goto")
def goto_pick():
    """Go to pick position"""
    if not controller.connected:
        return {"success": False, "message": "Not connected"}
    controller.go_to_pick()
    controller.get_position_from_encoder()
    return {"success": True, "position": controller.current_pos}


@app.post("/api/safe-z/set")
def set_safe_z():
    """Set current Z as safe height"""
    if not controller.connected:
        return {"success": False, "message": "Not connected"}
    controller.set_safe_z()
    return {"success": True, "safe_z": controller.positions['safe_z']}


@app.post("/api/safe-z/goto")
def goto_safe_z():
    """Go to safe Z height"""
    if not controller.connected:
        return {"success": False, "message": "Not connected"}
    controller.go_to_safe_z()
    controller.get_position_from_encoder()
    return {"success": True, "position": controller.current_pos}


@app.post("/api/hooks/add")
def add_hook():
    """Add current position as hook"""
    if not controller.connected:
        return {"success": False, "message": "Not connected"}
    idx = controller.add_hook()
    return {"success": True, "index": idx, "hooks": controller.positions['hooks']}


@app.delete("/api/hooks/{index}")
def delete_hook(index: int):
    """Delete a hook"""
    controller.delete_hook(index)
    return {"success": True, "hooks": controller.positions['hooks']}


class PositionRequest(BaseModel):
    x: float
    y: float
    z: float


@app.put("/api/hooks/{index}")
def update_hook(index: int, pos: PositionRequest):
    """Update a hook position"""
    if index < 0 or index >= len(controller.positions['hooks']):
        return {"success": False, "message": "Invalid hook index"}
    controller.positions['hooks'][index] = {'x': pos.x, 'y': pos.y, 'z': pos.z}
    controller.save_positions()
    return {"success": True, "hooks": controller.positions['hooks']}


@app.delete("/api/hooks")
def clear_hooks():
    """Clear all hooks"""
    controller.clear_all_hooks()
    return {"success": True}


@app.post("/api/hooks/{index}/goto")
def goto_hook(index: int):
    """Go to hook position"""
    if not controller.connected:
        return {"success": False, "message": "Not connected"}
    controller.go_to_hook(index)
    controller.get_position_from_encoder()
    return {"success": True, "position": controller.current_pos}


@app.post("/api/hooks/{index}/test")
def test_hook(index: int):
    """Test a single hook (pick and place)"""
    if not controller.connected:
        return {"success": False, "message": "Not connected"}
    
    def run():
        controller.test_single_hook(index)
    
    threading.Thread(target=run, daemon=True).start()
    return {"success": True, "message": "Test started"}


@app.post("/api/cycle/start")
def start_cycle():
    """Start full pick-and-place cycle"""
    if not controller.connected:
        return {"success": False, "message": "Not connected"}
    if not controller.positions.get('pick'):
        return {"success": False, "message": "Set pick location first"}
    if not controller.positions.get('hooks'):
        return {"success": False, "message": "Add hooks first"}
    
    def run():
        controller.run_full_cycle()
    
    threading.Thread(target=run, daemon=True).start()
    return {"success": True, "message": "Cycle started"}


@app.post("/api/cycle/pause")
def pause_cycle():
    """Pause/resume cycle"""
    if controller.pause_requested:
        controller.resume_cycle()
        return {"success": True, "paused": False}
    else:
        controller.pause_cycle()
        return {"success": True, "paused": True}


@app.post("/api/cycle/stop")
def stop_cycle():
    """Stop cycle"""
    controller.stop_cycle()
    return {"success": True}


@app.put("/api/settings")
def update_settings(req: SettingsRequest):
    """Update controller settings"""
    if req.suction_grab_delay is not None:
        controller.settings['suction_grab_delay'] = req.suction_grab_delay
    if req.suction_release_delay is not None:
        controller.settings['suction_release_delay'] = req.suction_release_delay
    if req.feedrate is not None:
        controller.settings['feedrate'] = req.feedrate
    return {"success": True, "settings": controller.settings}


@app.get("/api/position")
def get_position():
    """Get current position from encoder"""
    if not controller.connected:
        return {"success": False, "message": "Not connected"}
    pos = controller.get_position_from_encoder()
    return {"success": True, "position": pos}


# === WebSocket ===

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    clients.append(websocket)
    try:
        while True:
            # Send status updates periodically
            await websocket.send_json({
                "type": "status",
                "data": {
                    "connected": controller.connected,
                    "position": controller.current_pos,
                    "is_running": controller.is_running,
                    "is_paused": controller.pause_requested,
                }
            })
            await asyncio.sleep(0.5)
    except WebSocketDisconnect:
        clients.remove(websocket)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
