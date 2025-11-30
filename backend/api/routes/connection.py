"""
Connection Routes - Connect/disconnect and status

Updated for Phase 5 to use new BladeLoaderController.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional

from ..dependencies import get_app_state, AppState

router = APIRouter(tags=["connection"])


class ConnectRequest(BaseModel):
    port: str


@router.get("/ports")
def get_ports():
    """List available serial ports."""
    from core.serial_transport import SerialTransport
    return {"ports": SerialTransport.list_ports()}


@router.get("/status")
def get_status(state: AppState = Depends(get_app_state)):
    """Get current connection status and robot state."""
    return state.get_status()


@router.get("/history")
def get_history(limit: int = 50, state: AppState = Depends(get_app_state)):
    """Get recent command history."""
    return {"history": state.get_command_history(limit)}


@router.post("/connect")
def connect(req: ConnectRequest, state: AppState = Depends(get_app_state)):
    """Connect to DexArm."""
    try:
        success = state.connect(req.port)
        return {"success": success, "message": "Connected" if success else "Connection failed"}
    except Exception as e:
        return {"success": False, "message": str(e)}


@router.post("/disconnect")
def disconnect(state: AppState = Depends(get_app_state)):
    """Disconnect from DexArm."""
    state.disconnect()
    return {"success": True}
