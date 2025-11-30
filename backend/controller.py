"""
Blade Loader Controller - Main facade for the system.

Task 4.1: Controller Facade

Provides a simple, safe API for controlling the blade loader.
All motion goes through the MotionPlanner to enforce invariants.
"""

from __future__ import annotations

from typing import Dict, List, Any, TYPE_CHECKING

from core.types import (
    Position,
    HomeCommand,
    MoveCommand,
    WaitCommand,
    SuctionCommand,
    SetModuleCommand,
    MotorsCommand,
    DEFAULT_WORKSPACE,
)
from core.planner import MotionPlanner
from core.executor import CommandQueue, CommandResult
from core.logger import log_ok, log_move, log_sync, log_pos, log_critical, log_teach, log_warn
import re

if TYPE_CHECKING:
    from core.transport import Transport


class BladeLoaderController:
    """
    Main controller for the blade loader system.
    
    Provides a safe, high-level API for:
    - Homing
    - Movement (direct and safe)
    - Pick and place operations
    - Status reporting
    
    All movement uses MotionPlanner to enforce safety invariants.
    """
    
    def __init__(
        self,
        transport: "Transport",
        safe_z: float = 50.0,
        feedrate: int = 3000,
    ):
        self._transport = transport
        self._queue = CommandQueue()
        self._planner = MotionPlanner(
            safe_z=safe_z,
            feedrate=feedrate,
            workspace=DEFAULT_WORKSPACE,
        )
        
        self._position: Position = Position(0, 300, 0)
        self._is_homed: bool = False
        self._carrying_blade: bool = False
        self._suction_active: bool = False
        self._motors_enabled: bool = True  # Assume motors on at start
    
    # =========================================================================
    # Properties
    # =========================================================================
    
    @property
    def position(self) -> Position:
        """Current tracked position."""
        return self._position
    
    @property
    def safe_z(self) -> float:
        """Safe Z height."""
        return self._planner.safe_z
    
    def set_safe_z(self, z: float) -> None:
        """Update safe Z height in motion planner."""
        self._planner.safe_z = z
        log_ok(f"Safe Z updated to {z:.1f}")
    
    @property
    def is_homed(self) -> bool:
        """Whether arm has been homed."""
        return self._is_homed
    
    @property
    def carrying_blade(self) -> bool:
        """Whether currently carrying a blade."""
        return self._carrying_blade
    
    # =========================================================================
    # Core Operations
    # =========================================================================
    
    def home(self) -> None:
        """
        Home the arm.
        
        Must be called before any movement.
        If already homed, lifts to safe Z first to avoid collisions.
        Sends M1112 (DexArm home command).
        """
        # If already homed, lift to safe Z first for safety
        if self._is_homed and self._position.z < self._planner.safe_z:
            log_move(f"Lifting to safe Z={self._planner.safe_z} before homing")
            self._queue.enqueue(MoveCommand(z=self._planner.safe_z, feedrate=self._planner.feedrate))
            self._queue.enqueue(WaitCommand())
            self._queue.execute_all(self._transport)
        
        log_move("Homing to X=0 Y=300 Z=0")
        # Set pneumatic module
        self._queue.enqueue(SetModuleCommand("pneumatic"))
        
        # Home command
        self._queue.enqueue(HomeCommand())
        self._queue.enqueue(WaitCommand())
        
        self._queue.execute_all(self._transport)
        
        self._position = Position(0, 300, 0)
        self._is_homed = True
        self._carrying_blade = False
        log_ok("Homing complete")
    
    def move_to(self, target: Position) -> None:
        """
        Direct move to target position.
        
        WARNING: Does not lift Z first. Use safe_move_to when carrying blade.
        """
        self._require_homed()
        
        commands = self._planner.plan_direct_move(target)
        self._queue.enqueue_many(commands)
        self._queue.execute_all(self._transport)
        
        self._position = target
    
    def safe_move_to(self, target: Position) -> None:
        """
        Safe move to target: lifts Z first, then XY, then lowers.
        
        Always use this when carrying a blade.
        """
        self._require_homed()
        
        commands = self._planner.plan_safe_move(self._position, target)
        self._queue.enqueue_many(commands)
        self._queue.execute_all(self._transport)
        
        self._position = target
    
    def pick_blade(self, position: Position) -> None:
        """
        Pick a blade from the given position.
        
        Sequence:
        1. Safe move to above pick position
        2. Turn on suction
        3. Lower to pick
        4. Wait for vacuum
        5. Lift to safe Z
        """
        self._require_homed()
        
        commands = self._planner.plan_pick_sequence(self._position, position)
        self._queue.enqueue_many(commands)
        self._queue.execute_all(self._transport)
        
        self._position = position.with_z(self._planner.safe_z)
        self._carrying_blade = True
        self._suction_active = True
    
    def place_blade(self, position: Position) -> None:
        """
        Place a blade at the given position.
        
        Sequence:
        1. Safe move to above place position
        2. Lower to place
        3. Release suction
        4. Wait
        5. Turn off pump
        6. Lift to safe Z
        """
        self._require_homed()
        
        if not self._carrying_blade:
            raise RuntimeError("Cannot place: not carrying a blade")
        
        commands = self._planner.plan_place_sequence(self._position, position)
        self._queue.enqueue_many(commands)
        self._queue.execute_all(self._transport)
        
        self._position = position.with_z(self._planner.safe_z)
        self._carrying_blade = False
        self._suction_active = False
    
    # =========================================================================
    # Suction Control
    # =========================================================================
    
    def suction_on(self) -> None:
        """Turn on suction (M1000)."""
        self._queue.enqueue(SuctionCommand("on"))
        self._queue.execute_all(self._transport)
        self._suction_active = True
    
    def suction_off(self) -> None:
        """Turn off suction pump (M1003)."""
        self._queue.enqueue(SuctionCommand("release"))
        self._queue.enqueue(SuctionCommand("off"))
        self._queue.execute_all(self._transport)
        self._suction_active = False
    
    # =========================================================================
    # Motor Control
    # =========================================================================
    
    def motors_off(self) -> None:
        """
        Disable motors (teach mode).
        
        Allows manual positioning of the arm.
        WARNING: Position tracking becomes invalid until motors_on() is called.
        """
        if self._carrying_blade:
            log_warn("WARNING: Entering teach mode while carrying blade!")
        
        log_teach("Motors OFF - entering teach mode")
        self._queue.enqueue(MotorsCommand(enable=False))
        self._queue.execute_all(self._transport)
        self._motors_enabled = False
    
    def motors_on(self) -> None:
        """
        Enable motors and sync position after teach mode.
        
        CRITICAL: Must read actual position before any movement,
        otherwise motion planning will be wrong (causing jerky moves).
        """
        log_teach("Motors ON - exiting teach mode, syncing position...")
        self._queue.enqueue(MotorsCommand(enable=True))
        self._queue.execute_all(self._transport)
        self._motors_enabled = True
        
        # Sync our tracked position with reality
        self.sync_position()
    
    def sync_position(self) -> Position:
        """
        Sync internal position tracking with actual arm position.
        
        MUST be called:
        - After exiting teach mode (before any movement)
        - Before starting cycles
        - Any time position might be out of sync
        
        Uses M895 to read encoder → Cartesian.
        """
        pos = self.read_position_from_sensor()
        log_sync(f"Position synced: X={pos.x:.1f} Y={pos.y:.1f} Z={pos.z:.1f}")
        return pos
    
    def read_position_from_sensor(self) -> Position:
        """
        Read actual Cartesian position from encoder sensors using M895.
        
        M895 reads the magnetic encoders and converts to Cartesian coordinates.
        This works correctly even after teach mode (M84) when arm was moved by hand.
        
        Response format: "X:100.00 Y:200.00 Z:50.00"
        """
        response = self._transport.send("M895")
        log_pos(f"M895 raw response: {repr(response)}")
        
        # Parse response like "X:100.00 Y:200.00 Z:50.00"
        x_match = re.search(r'X[:\s]*([-\d.]+)', response)
        y_match = re.search(r'Y[:\s]*([-\d.]+)', response)
        z_match = re.search(r'Z[:\s]*([-\d.]+)', response)
        
        if x_match and y_match and z_match:
            pos = Position(
                float(x_match.group(1)),
                float(y_match.group(1)),
                float(z_match.group(1))
            )
            # Update tracked position to match actual
            self._position = pos
            log_pos(f"Parsed: X={pos.x:.1f} Y={pos.y:.1f} Z={pos.z:.1f}")
            return pos
        else:
            log_critical(f"Could not parse M895 response: {response}")
            log_warn(f"Using stale position: {self._position}")
            return self._position
    
    # =========================================================================
    # Status & History
    # =========================================================================
    
    def get_status(self) -> Dict[str, Any]:
        """Get current controller status."""
        return {
            "position": self._position.to_dict(),
            "homed": self._is_homed,
            "carrying_blade": self._carrying_blade,
            "suction_active": self._suction_active,
            "motors_enabled": self._motors_enabled,
            "safe_z": self._planner.safe_z,
        }
    
    def get_command_history(self, limit: int | None = None) -> List[CommandResult]:
        """Get command execution history."""
        return self._queue.get_history(limit)
    
    def print_history(self, limit: int = 20) -> None:
        """Print recent command history."""
        self._queue.print_history(limit)
    
    # =========================================================================
    # Internals
    # =========================================================================
    
    def _require_homed(self) -> None:
        """Raise error if not homed or motors disabled."""
        if not self._is_homed:
            raise RuntimeError("Must home before moving")
        if not self._motors_enabled:
            log_warn("Motors disabled - syncing position first")
            self.motors_on()  # Auto-recover by enabling motors
