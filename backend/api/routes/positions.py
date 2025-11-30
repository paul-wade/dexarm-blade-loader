"""
Positions Routes - Pick, hooks, safe-z management

Updated for Phase 5 to use BladeLoaderController.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from core.types import Position, DEFAULT_WORKSPACE
from core.logger import log_pos, log_warn
from ..dependencies import get_app_state, require_homed, require_connection, AppState

router = APIRouter(tags=["positions"])


class PositionRequest(BaseModel):
    x: float
    y: float
    z: float


# === Pick Position ===

@router.post("/pick/set")
def set_pick(pos: PositionRequest, state: AppState = Depends(get_app_state)):
    """Set pick position."""
    state.positions.set_pick(Position(pos.x, pos.y, pos.z))
    pick = state.positions.get_pick()
    return {"success": True, "pick": pick.to_dict() if pick else None}


@router.post("/pick/set_current")
def set_pick_current(state: AppState = Depends(get_app_state)):
    """
    Set current position as pick point.
    
    Uses M895 to read actual Cartesian position from encoder sensors.
    Does NOT change motor state - user controls teach mode.
    """
    ctrl = require_homed()
    
    # Read actual position using M895 (encoder -> Cartesian)
    pos = ctrl.read_position_from_sensor()
    log_pos(f"Setting pick at X={pos.x:.1f} Y={pos.y:.1f} Z={pos.z:.1f}")
    
    state.positions.set_pick(pos)
    
    return {"success": True, "pick": pos.to_dict()}


@router.post("/pick/goto")
def goto_pick(state: AppState = Depends(get_app_state)):
    """Go to pick position (safe movement)."""
    ctrl = require_homed()
    pick = state.positions.get_pick()
    if not pick:
        raise HTTPException(status_code=400, detail="Pick position not set")
    
    try:
        ctrl.safe_move_to(pick)  # pick is already a Position
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    return {"success": True, "position": ctrl.position.to_dict()}


@router.get("/pick")
def get_pick(state: AppState = Depends(get_app_state)):
    """Get pick position."""
    pick = state.positions.get_pick()
    return {"pick": pick.to_dict() if pick else None}


# === Safe Z ===

@router.post("/safe-z/set")
def set_safe_z(z: float, state: AppState = Depends(get_app_state)):
    """Set safe Z height."""
    state.positions.set_safe_z(z)
    # Also update the controller's planner
    if state.controller:
        state.controller.set_safe_z(z)
    return {"success": True, "safe_z": z}


@router.post("/safe-z/set_current")
def set_safe_z_current(state: AppState = Depends(get_app_state)):
    """
    Set current Z as safe height.
    
    Uses M895 to read actual Cartesian position from encoder sensors.
    Does NOT change motor state - user controls teach mode.
    """
    ctrl = require_homed()
    
    # Read actual position using M895 (encoder -> Cartesian)
    pos = ctrl.read_position_from_sensor()
    log_pos(f"Setting safe_z={pos.z:.1f}")
    
    z = pos.z
    state.positions.set_safe_z(z)
    # Also update the controller's planner
    ctrl.set_safe_z(z)
    
    return {"success": True, "safe_z": z}


@router.post("/safe-z/goto")
def goto_safe_z(state: AppState = Depends(get_app_state)):
    """Go to safe Z height."""
    ctrl = require_homed()
    safe_z = state.positions.get_safe_z() or 50.0
    target = ctrl.position.with_z(safe_z)
    ctrl.move_to(target)
    return {"success": True, "position": ctrl.position.to_dict()}


@router.get("/safe-z")
def get_safe_z(state: AppState = Depends(get_app_state)):
    """Get safe Z height."""
    return {"safe_z": state.positions.get_safe_z()}


# === Hooks ===

@router.post("/hooks/add")
def add_hook(pos: PositionRequest, state: AppState = Depends(get_app_state)):
    """Add hook at position."""
    idx = state.positions.add_hook(Position(pos.x, pos.y, pos.z))
    return {"success": True, "index": idx, "hooks": [h.to_dict() for h in state.positions.get_hooks()]}


@router.post("/hooks/add_current")
def add_hook_current(state: AppState = Depends(get_app_state)):
    """
    Add current position as hook.
    
    Uses M895 to read actual Cartesian position from encoder sensors.
    Does NOT change motor state - user controls teach mode.
    Validates position is within workspace before saving.
    """
    ctrl = require_homed()
    
    # Read actual position using M895 (encoder -> Cartesian)
    # This works whether motors are on or off
    pos = ctrl.read_position_from_sensor()
    log_pos(f"Adding hook at X={pos.x:.1f} Y={pos.y:.1f} Z={pos.z:.1f}")
    
    # VALIDATE position is within workspace
    valid, msg = DEFAULT_WORKSPACE.validate(pos)
    if not valid:
        log_warn(f"Hook position INVALID: {msg}")
        raise HTTPException(status_code=400, detail=f"Position out of workspace: {msg}")
    
    idx = state.positions.add_hook(pos)
    
    return {
        "success": True, 
        "index": idx, 
        "position": pos.to_dict(),
        "hooks": [h.to_dict() for h in state.positions.get_hooks()]
    }


@router.delete("/hooks/{index}")
def delete_hook(index: int, state: AppState = Depends(get_app_state)):
    """Delete a hook."""
    state.positions.delete_hook(index)
    return {"success": True, "hooks": [h.to_dict() for h in state.positions.get_hooks()]}


@router.put("/hooks/{index}")
def update_hook(index: int, pos: PositionRequest, state: AppState = Depends(get_app_state)):
    """Update a hook position."""
    success = state.positions.update_hook(index, Position(pos.x, pos.y, pos.z))
    if not success:
        return {"success": False, "message": "Invalid hook index"}
    return {"success": True, "hooks": [h.to_dict() for h in state.positions.get_hooks()]}


@router.delete("/hooks")
def clear_hooks(state: AppState = Depends(get_app_state)):
    """Clear all hooks."""
    state.positions.clear_hooks()
    return {"success": True}


@router.get("/hooks")
def get_hooks(state: AppState = Depends(get_app_state)):
    """Get all hooks."""
    return {"hooks": [h.to_dict() for h in state.positions.get_hooks()]}


@router.post("/hooks/{index}/goto")
def goto_hook(index: int, state: AppState = Depends(get_app_state)):
    """Go to hook position (safe movement)."""
    ctrl = require_homed()
    hook = state.positions.get_hook(index)
    if not hook:
        raise HTTPException(status_code=400, detail="Invalid hook index")
    
    try:
        ctrl.safe_move_to(hook)  # hook is already a Position
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    return {"success": True, "position": ctrl.position.to_dict()}


@router.post("/hooks/{index}/test")
def test_hook(index: int, state: AppState = Depends(get_app_state)):
    """
    Test a hook by doing a full pick-place cycle to it.
    
    Picks from stored pick position, places at this hook, returns home.
    """
    ctrl = require_homed()
    
    pick = state.positions.get_pick()
    if not pick:
        raise HTTPException(status_code=400, detail="Pick position not set")
    
    hook = state.positions.get_hook(index)
    if not hook:
        raise HTTPException(status_code=400, detail="Invalid hook index")
    
    try:
        # Pick blade
        ctrl.pick_blade(pick)
        
        # Place at hook
        ctrl.place_blade(hook)
        
        # Return to safe Z
        safe_z = state.positions.get_safe_z() or 50.0
        ctrl.safe_move_to(Position(ctrl.position.x, ctrl.position.y, safe_z))
        
    except (ValueError, RuntimeError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    return {"success": True, "position": ctrl.position.to_dict()}
