"""
Movement Routes - Home, jog, move, position queries

Updated for Phase 5 to use BladeLoaderController.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from core.types import Position
from ..dependencies import get_app_state, require_connection, require_homed, AppState

router = APIRouter(tags=["movement"])


class MoveRequest(BaseModel):
    x: float
    y: float
    z: float


class JogRequest(BaseModel):
    axis: str
    distance: float


@router.post("/home")
def go_home():
    """
    Move to home position.
    
    Sends M1112 (DexArm home command).
    """
    ctrl = require_connection()
    ctrl.home()
    return {"success": True, "position": ctrl.position.to_dict()}


@router.post("/move")
def move_to(req: MoveRequest):
    """Direct move to position."""
    ctrl = require_homed()
    target = Position(req.x, req.y, req.z)
    ctrl.move_to(target)
    return {"success": True, "position": ctrl.position.to_dict()}


@router.post("/safe_move")
def safe_move_to(req: MoveRequest):
    """
    Safe move to position.
    
    Lifts Z to safe height before XY movement.
    """
    ctrl = require_homed()
    target = Position(req.x, req.y, req.z)
    ctrl.safe_move_to(target)
    return {"success": True, "position": ctrl.position.to_dict()}


@router.post("/jog")
def jog(req: JogRequest):
    """Jog a single axis by distance."""
    ctrl = require_homed()
    
    current = ctrl.position
    if req.axis.lower() == 'x':
        target = Position(current.x + req.distance, current.y, current.z)
    elif req.axis.lower() == 'y':
        target = Position(current.x, current.y + req.distance, current.z)
    elif req.axis.lower() == 'z':
        target = Position(current.x, current.y, current.z + req.distance)
    else:
        raise HTTPException(status_code=400, detail=f"Invalid axis: {req.axis}")
    
    try:
        ctrl.move_to(target)
    except ValueError as e:
        # Position out of bounds - return 400 not 500
        raise HTTPException(status_code=400, detail=str(e))
    
    return {"success": True, "position": ctrl.position.to_dict()}


@router.post("/teach/enable")
def enable_teach_mode():
    """Enable free movement mode (motors off)."""
    ctrl = require_connection()
    ctrl.motors_off()
    return {"success": True}


@router.post("/teach/disable")
def disable_teach_mode():
    """Disable free movement mode (motors on)."""
    ctrl = require_connection()
    ctrl.motors_on()
    return {"success": True, "position": ctrl.position.to_dict()}


@router.get("/position")
def get_position():
    """Get current tracked position."""
    ctrl = require_connection()
    return {"success": True, "position": ctrl.position.to_dict()}


@router.post("/estop")
def emergency_stop(state: AppState = Depends(get_app_state)):
    """
    EMERGENCY STOP - immediately halt all movement.
    
    Uses M410 (quickstop, can resume) NOT M112 (requires reboot).
    """
    if state.controller:
        from core.types import EmergencyStopCommand
        state.controller._queue.execute_immediate(
            EmergencyStopCommand(), 
            state._transport
        )
        state.controller.suction_off()
    
    state.is_running = False
    
    return {"success": True, "message": "EMERGENCY STOP - recommend re-homing"}
