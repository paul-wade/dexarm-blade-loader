"""
API Dependencies - Dependency injection for FastAPI

Task 5.1: Updated to use new BladeLoaderController architecture.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
import sys
import os

# Add parent to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.types import Position
from core.transport import MockTransport
from core.serial_transport import SerialTransport
from core.position_store import PositionStore
from controller import BladeLoaderController


@dataclass
class AppState:
    """
    Application state container.
    
    Uses the new BladeLoaderController which enforces all safety invariants.
    """
    positions: PositionStore = field(default_factory=PositionStore)
    controller: Optional[BladeLoaderController] = None
    _transport: Optional[Any] = None
    
    # Workflow state
    is_running: bool = False
    is_paused: bool = False
    current_cycle: int = 0
    total_cycles: int = 0
    
    @property
    def is_connected(self) -> bool:
        return self._transport is not None and self._transport.is_connected
    
    def connect(self, port: str) -> bool:
        """Connect to robot and initialize controller."""
        try:
            # Use mock for testing, real serial for production
            if port == "mock":
                self._transport = MockTransport()
            else:
                self._transport = SerialTransport()
                if not self._transport.connect(port):
                    return False
            
            # Create controller with configured safe_z
            safe_z = self.positions.get_safe_z() or 50.0
            self.controller = BladeLoaderController(
                transport=self._transport,
                safe_z=safe_z,
                feedrate=3000,
            )
            
            return True
        except Exception as e:
            print(f"Connection error: {e}")
            return False
    
    def disconnect(self) -> None:
        """Disconnect from robot."""
        if hasattr(self._transport, 'disconnect'):
            self._transport.disconnect()
        self._transport = None
        self.controller = None
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status for API."""
        if self.controller:
            ctrl_status = self.controller.get_status()
            return {
                "connected": True,
                "homed": ctrl_status["homed"],
                "position": ctrl_status["position"],
                "carrying_blade": ctrl_status["carrying_blade"],
                "suction_active": ctrl_status["suction_active"],
                "motors_enabled": ctrl_status["motors_enabled"],
                "safe_z": ctrl_status["safe_z"],
                "is_running": self.is_running,
                "is_paused": self.is_paused,
                "current_cycle": self.current_cycle,
                "total_cycles": self.total_cycles,
                "positions": self.positions.to_dict(),
            }
        else:
            return {
                "connected": False,
                "homed": False,
                "position": {"x": 0, "y": 300, "z": 0},
                "carrying_blade": False,
                "suction_active": False,
                "motors_enabled": True,
                "safe_z": 50.0,
                "is_running": False,
                "is_paused": False,
                "current_cycle": 0,
                "total_cycles": 0,
                "positions": self.positions.to_dict(),
            }
    
    def get_command_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent command history."""
        if not self.controller:
            return []
        
        history = self.controller.get_command_history(limit)
        return [
            {
                "gcode": r.gcode,
                "response": r.response,
                "success": r.success,
                "timestamp": r.timestamp.isoformat(),
            }
            for r in history
        ]


# Global instance
_app_state: Optional[AppState] = None


def get_app_state() -> AppState:
    """Get the global app state instance."""
    global _app_state
    if _app_state is None:
        _app_state = AppState()
    return _app_state


def require_connection() -> BladeLoaderController:
    """Get controller, raising error if not connected."""
    from fastapi import HTTPException
    
    state = get_app_state()
    if not state.is_connected or state.controller is None:
        raise HTTPException(status_code=400, detail="Not connected to robot")
    return state.controller


def require_homed() -> BladeLoaderController:
    """Get controller, raising error if not connected or homed."""
    from fastapi import HTTPException
    
    ctrl = require_connection()
    if not ctrl.is_homed:
        raise HTTPException(status_code=400, detail="Robot not homed")
    return ctrl
