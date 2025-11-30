"""
Core immutable types for the blade loader system.

Task 1.1: Immutable Data Types

All types are frozen dataclasses to prevent accidental mutation.
This ensures command sequences are deterministic and testable.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal, Optional, Protocol, Tuple


# =============================================================================
# Position Types
# =============================================================================


@dataclass(frozen=True)
class Position:
    """
    Immutable 3D position in mm.
    
    Coordinate system (from DexArm docs):
    - X: left/right (0 = center)
    - Y: forward (300 = home, cannot go behind base ~100)
    - Z: up/down (0 = home height)
    """
    x: float
    y: float
    z: float

    def distance_to(self, other: Position) -> float:
        """Euclidean distance to another position."""
        return math.sqrt(
            (self.x - other.x) ** 2 +
            (self.y - other.y) ** 2 +
            (self.z - other.z) ** 2
        )

    def xy_distance_to(self, other: Position) -> float:
        """Distance in XY plane only (ignores Z)."""
        return math.sqrt(
            (self.x - other.x) ** 2 +
            (self.y - other.y) ** 2
        )

    def reach(self) -> float:
        """Distance from origin in XY plane (arm reach)."""
        return math.sqrt(self.x ** 2 + self.y ** 2)

    def with_z(self, new_z: float) -> Position:
        """Create new position with different Z."""
        return Position(self.x, self.y, new_z)

    def with_xy(self, new_x: float, new_y: float) -> Position:
        """Create new position with different XY."""
        return Position(new_x, new_y, self.z)

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {"x": self.x, "y": self.y, "z": self.z}

    @classmethod
    def from_dict(cls, d: dict) -> Position:
        """Deserialize from dictionary."""
        return cls(x=d["x"], y=d["y"], z=d["z"])


@dataclass(frozen=True)
class WorkspaceLimits:
    """
    DexArm workspace boundaries.
    
    These are hardware limits - exceeding them can damage the arm.
    """
    x_min: float
    x_max: float
    y_min: float
    y_max: float
    z_min: float
    z_max: float
    max_reach: float  # sqrt(x^2 + y^2) limit

    def validate(self, pos: Position) -> Tuple[bool, str]:
        """
        Check if position is within workspace.
        
        Returns:
            (valid, message) - message is "OK" if valid, else describes violation
        """
        if not (self.x_min <= pos.x <= self.x_max):
            return False, f"X={pos.x:.1f} out of range [{self.x_min}, {self.x_max}]"
        
        if not (self.y_min <= pos.y <= self.y_max):
            return False, f"Y={pos.y:.1f} out of range [{self.y_min}, {self.y_max}]"
        
        if not (self.z_min <= pos.z <= self.z_max):
            return False, f"Z={pos.z:.1f} out of range [{self.z_min}, {self.z_max}]"
        
        reach = pos.reach()
        if reach > self.max_reach:
            return False, f"Reach={reach:.1f}mm exceeds max {self.max_reach}mm"
        
        return True, "OK"


# Default workspace for DexArm
# Note: Standard reach is ~320mm but actual usable space may vary
# based on mounting and configuration. Set conservatively high.
DEFAULT_WORKSPACE = WorkspaceLimits(
    x_min=-300,
    x_max=300,
    y_min=100,   # Can't go behind base
    y_max=450,
    z_min=-100,  # Allow lower for blade picking
    z_max=200,
    max_reach=400,  # Allow extended positions - arm will error if truly unreachable
)


# =============================================================================
# Command Protocol & Types
# =============================================================================


class Command(Protocol):
    """Protocol for all G-code commands."""
    
    def to_gcode(self) -> str:
        """Convert to G-code string."""
        ...


@dataclass(frozen=True)
class MoveCommand:
    """
    Linear move command (G1).
    
    At least one axis must be specified.
    Axes not specified will not be included in G-code (arm keeps current value).
    """
    x: Optional[float] = None
    y: Optional[float] = None
    z: Optional[float] = None
    feedrate: int = 3000

    def __post_init__(self):
        if self.x is None and self.y is None and self.z is None:
            raise ValueError("MoveCommand requires at least one axis (x, y, or z)")

    def to_gcode(self) -> str:
        """Generate G1 command."""
        parts = [f"G1 F{self.feedrate}"]
        if self.x is not None:
            parts.append(f"X{self.x:.2f}")
        if self.y is not None:
            parts.append(f"Y{self.y:.2f}")
        if self.z is not None:
            parts.append(f"Z{self.z:.2f}")
        return " ".join(parts)

    def changes_xy(self) -> bool:
        """Does this command change X or Y?"""
        return self.x is not None or self.y is not None

    def changes_z(self) -> bool:
        """Does this command change Z?"""
        return self.z is not None

    def is_z_only(self) -> bool:
        """Is this a Z-only move?"""
        return self.z is not None and self.x is None and self.y is None

    def is_xy_only(self) -> bool:
        """Is this an XY-only move (no Z)?"""
        return (self.x is not None or self.y is not None) and self.z is None


@dataclass(frozen=True)
class WaitCommand:
    """Wait for moves to complete (M400)."""

    def to_gcode(self) -> str:
        return "M400"


@dataclass(frozen=True)
class HomeCommand:
    """Home the arm (M1112 - DexArm specific, NOT M112!)."""

    def to_gcode(self) -> str:
        return "M1112"


@dataclass(frozen=True)
class SuctionCommand:
    """
    Control pneumatic suction.
    
    Actions:
    - "on": M1000 - Pump IN (suction grabs object)
    - "blow": M1001 - Pump OUT (blow air)
    - "release": M1002 - Release pressure (neutral)
    - "off": M1003 - Stop pump
    """
    action: Literal["on", "blow", "release", "off"]

    def to_gcode(self) -> str:
        codes = {
            "on": "M1000",
            "blow": "M1001",
            "release": "M1002",
            "off": "M1003",
        }
        return codes[self.action]


@dataclass(frozen=True)
class DelayCommand:
    """Dwell/delay command (G4)."""
    milliseconds: int

    def to_gcode(self) -> str:
        return f"G4 P{self.milliseconds}"


@dataclass(frozen=True)
class SetModuleCommand:
    """Set front-end module (M888)."""
    module: Literal["pen", "laser", "pneumatic", "3d_print"]

    def to_gcode(self) -> str:
        codes = {
            "pen": "M888 P0",
            "laser": "M888 P1",
            "pneumatic": "M888 P2",
            "3d_print": "M888 P3",
        }
        return codes[self.module]


@dataclass(frozen=True)
class GetPositionCommand:
    """Query current position (M114)."""

    def to_gcode(self) -> str:
        return "M114"


@dataclass(frozen=True)
class MotorsCommand:
    """Enable/disable motors."""
    enable: bool

    def to_gcode(self) -> str:
        return "M17" if self.enable else "M84"


@dataclass(frozen=True)
class EmergencyStopCommand:
    """
    Emergency stop (M410 - quickstop, can resume).
    
    WARNING: M112 is full emergency stop requiring reboot - we use M410 instead.
    """

    def to_gcode(self) -> str:
        return "M410"


# =============================================================================
# State Types
# =============================================================================


@dataclass(frozen=True)
class ArmState:
    """
    Immutable snapshot of arm state.
    
    Used for tracking and decision making.
    """
    position: Position
    carrying_blade: bool = False
    suction_active: bool = False
    motors_enabled: bool = True
    homed: bool = False

    def with_position(self, pos: Position) -> ArmState:
        """Create new state with updated position."""
        return ArmState(
            position=pos,
            carrying_blade=self.carrying_blade,
            suction_active=self.suction_active,
            motors_enabled=self.motors_enabled,
            homed=self.homed,
        )

    def with_carrying(self, carrying: bool) -> ArmState:
        """Create new state with updated carrying status."""
        return ArmState(
            position=self.position,
            carrying_blade=carrying,
            suction_active=self.suction_active,
            motors_enabled=self.motors_enabled,
            homed=self.homed,
        )

    def with_suction(self, active: bool) -> ArmState:
        """Create new state with updated suction status."""
        return ArmState(
            position=self.position,
            carrying_blade=self.carrying_blade,
            suction_active=active,
            motors_enabled=self.motors_enabled,
            homed=self.homed,
        )
