"""
Suction Routes - Suction pump control

Updated for Phase 5 to use BladeLoaderController.
"""

from fastapi import APIRouter

from core.types import SuctionCommand
from ..dependencies import require_connection, get_app_state

router = APIRouter(prefix="/suction", tags=["suction"])


@router.post("/on")
def suction_on():
    """M1000 - Turn suction pump ON (vacuum to grab)."""
    ctrl = require_connection()
    ctrl.suction_on()
    return {"success": True}


@router.post("/off")
def suction_off():
    """M1003 - Turn suction pump OFF."""
    ctrl = require_connection()
    ctrl.suction_off()
    return {"success": True}


@router.post("/blow")
def suction_blow():
    """M1001 - Blow air out (pump out)."""
    ctrl = require_connection()
    state = get_app_state()
    ctrl._queue.execute_immediate(SuctionCommand("blow"), state._transport)
    return {"success": True}


@router.post("/release")
def suction_release():
    """M1002 - Release air pressure to neutral."""
    ctrl = require_connection()
    state = get_app_state()
    ctrl._queue.execute_immediate(SuctionCommand("release"), state._transport)
    return {"success": True}
