"""
Cycles Routes - Pick/place operations

Updated for Phase 5 to use BladeLoaderController.
"""

import time

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional

from core.types import Position
from core.logger import log_cycle, log_ok, log_critical
from ..dependencies import get_app_state, require_homed, AppState

router = APIRouter(prefix="/cycle", tags=["cycles"])


class PickPlaceRequest(BaseModel):
    x: float
    y: float
    z: float


@router.post("/pick")
def pick_blade(req: PickPlaceRequest):
    """
    Pick a blade from specified position.
    
    Uses safe motion (lifts Z before XY).
    """
    ctrl = require_homed()
    target = Position(req.x, req.y, req.z)
    ctrl.pick_blade(target)
    return {
        "success": True,
        "position": ctrl.position.to_dict(),
        "carrying_blade": ctrl.carrying_blade,
    }


@router.post("/place")
def place_blade(req: PickPlaceRequest):
    """
    Place a blade at specified position.
    
    Uses safe motion (lifts Z before XY).
    """
    ctrl = require_homed()
    target = Position(req.x, req.y, req.z)
    
    try:
        ctrl.place_blade(target)
    except RuntimeError as e:
        return {"success": False, "message": str(e)}
    
    return {
        "success": True,
        "position": ctrl.position.to_dict(),
        "carrying_blade": ctrl.carrying_blade,
    }


@router.post("/pick_from_stored")
def pick_from_stored(state: AppState = Depends(get_app_state)):
    """Pick blade from stored pick position."""
    ctrl = require_homed()
    
    pick_pos = state.positions.get_pick()
    if not pick_pos:
        return {"success": False, "message": "No pick position set"}
    
    ctrl.pick_blade(pick_pos)  # already a Position
    
    return {
        "success": True,
        "position": ctrl.position.to_dict(),
        "carrying_blade": ctrl.carrying_blade,
    }


@router.post("/place_at_hook/{index}")
def place_at_hook(index: int, state: AppState = Depends(get_app_state)):
    """Place blade at stored hook position."""
    ctrl = require_homed()
    
    hook_pos = state.positions.get_hook(index)
    if not hook_pos:
        return {"success": False, "message": f"No hook at index {index}"}
    
    ctrl.place_blade(hook_pos)  # already a Position
    
    return {
        "success": True,
        "position": ctrl.position.to_dict(),
        "carrying_blade": ctrl.carrying_blade,
    }


@router.post("/run")
def run_full_cycle(state: AppState = Depends(get_app_state)):
    """
    Run complete pick-place cycle for all hooks.
    
    Picks from stored pick position, places at each hook in order.
    """
    ctrl = require_homed()
    
    pick_pos = state.positions.get_pick()
    if not pick_pos:
        return {"success": False, "message": "No pick position set"}
    
    hook_count = state.positions.hook_count()
    if hook_count == 0:
        return {"success": False, "message": "No hooks defined"}
    
    if state.is_running:
        return {"success": False, "message": "Cycle already running"}
    
    # CRITICAL: Sync position before starting - ensures we know where arm actually is
    ctrl.sync_position()
    log_cycle(f"Starting cycle at X={ctrl.position.x:.1f} Y={ctrl.position.y:.1f} Z={ctrl.position.z:.1f}")
    
    state.is_running = True
    state.is_paused = False
    state.total_cycles = hook_count
    
    try:
        for i in range(hook_count):
            if not state.is_running:
                break  # Stop requested
            
            while state.is_paused:
                time.sleep(0.1)  # Wait while paused
                if not state.is_running:
                    break
            
            state.current_cycle = i + 1
            
            # Pick
            log_cycle(f"Cycle {i+1}/{hook_count}: PICKING from X={pick_pos.x:.1f} Y={pick_pos.y:.1f} Z={pick_pos.z:.1f}")
            ctrl.pick_blade(pick_pos)
            
            # Place
            hook = state.positions.get_hook(i)
            log_cycle(f"Cycle {i+1}/{hook_count}: PLACING at hook {i} X={hook.x:.1f} Y={hook.y:.1f} Z={hook.z:.1f}")
            ctrl.place_blade(hook)
        
        log_ok(f"Cycle complete: {hook_count} blades placed")
        return {
            "success": True,
            "message": f"Completed {hook_count} cycles",
            "position": ctrl.position.to_dict(),
        }
    
    except Exception as e:
        log_critical(f"Cycle FAILED: {e}")
        # SAFETY: Turn off pump on error to prevent vacuum lock
        try:
            ctrl.suction_off()
        except:
            pass
        return {"success": False, "message": str(e)}
    
    finally:
        state.is_running = False
        state.is_paused = False
        state.current_cycle = 0
        # SAFETY: Always ensure pump is off when cycle ends
        try:
            if ctrl._suction_active:
                ctrl.suction_off()
        except:
            pass


@router.post("/pause")
def pause_cycle(state: AppState = Depends(get_app_state)):
    """Pause/resume running cycle."""
    if state.is_running:
        state.is_paused = not state.is_paused
    return {"success": True, "paused": state.is_paused}


@router.post("/stop")
def stop_cycle(state: AppState = Depends(get_app_state)):
    """Stop running cycle and turn off pump."""
    state.is_running = False
    state.is_paused = False
    
    # SAFETY: Turn off pump when stopping
    if state.controller:
        try:
            state.controller.suction_off()
        except:
            pass
    
    return {"success": True}


@router.get("/state")
def get_cycle_state(state: AppState = Depends(get_app_state)):
    """Get current cycle state."""
    return {
        "is_running": state.is_running,
        "is_paused": state.is_paused,
        "current_cycle": state.current_cycle,
        "total_cycles": state.total_cycles,
    }
