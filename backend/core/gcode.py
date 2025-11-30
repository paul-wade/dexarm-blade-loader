"""
G-Code Builder - Single responsibility: building G-code commands
"""

import time
from dataclasses import dataclass
from typing import Optional
from .serial_transport import ISerialTransport


@dataclass
class Position:
    """3D position"""
    x: float
    y: float
    z: float
    
    def to_dict(self) -> dict:
        return {'x': self.x, 'y': self.y, 'z': self.z}
    
    @classmethod
    def from_dict(cls, d: dict) -> 'Position':
        return cls(x=d['x'], y=d['y'], z=d['z'])


class GCodeBuilder:
    """Builds G-code command strings"""
    
    @staticmethod
    def move(x: Optional[float] = None, 
             y: Optional[float] = None, 
             z: Optional[float] = None,
             feedrate: Optional[int] = None) -> str:
        """Build G1 move command"""
        parts = ["G1"]
        if feedrate:
            parts.append(f"F{feedrate}")
        if x is not None:
            parts.append(f"X{x:.2f}")
        if y is not None:
            parts.append(f"Y{y:.2f}")
        if z is not None:
            parts.append(f"Z{z:.2f}")
        return " ".join(parts)
    
    @staticmethod
    def move_xyz(x: float, y: float, z: float, feedrate: int) -> str:
        """Build full XYZ move command"""
        return f"G1 F{feedrate} X{x:.2f} Y{y:.2f} Z{z:.2f}"
    
    @staticmethod
    def move_z(z: float, feedrate: int) -> str:
        """Build Z-only move command"""
        return f"G1 F{feedrate} Z{z:.2f}"
    
    @staticmethod
    def move_xy(x: float, y: float, feedrate: int) -> str:
        """Build XY-only move command"""
        return f"G1 F{feedrate} X{x:.2f} Y{y:.2f}"
    
    @staticmethod
    def home() -> str:
        """DexArm home command"""
        return "M1112"
    
    @staticmethod
    def wait_for_move() -> str:
        """Wait for moves to complete"""
        return "M400"
    
    @staticmethod
    def emergency_stop() -> str:
        """M410 - Emergency stop all steppers immediately"""
        return "M410"
    
    @staticmethod
    def get_position() -> str:
        """Query current position"""
        return "M114"
    
    @staticmethod
    def get_encoder_position() -> str:
        """Query encoder position"""
        return "M893"
    
    @staticmethod
    def set_module(module_type: int) -> str:
        """Set front-end module"""
        return f"M888 P{module_type}"
    
    @staticmethod
    def suction_on() -> str:
        """M1000 - Pump IN (suction cup grabs)"""
        return "M1000"
    
    @staticmethod
    def suction_blow() -> str:
        """M1001 - Pump OUT (blow air to release object)"""
        return "M1001"
    
    @staticmethod
    def suction_release() -> str:
        """M1002 - Release air (return to neutral)"""
        return "M1002"
    
    @staticmethod
    def suction_off() -> str:
        """M1003 - Stop air pump"""
        return "M1003"
    
    @staticmethod
    def motors_off() -> str:
        """Disable motors (teach mode)"""
        return "M84"
    
    @staticmethod
    def motors_on() -> str:
        """Enable motors"""
        return "M17"
    
    @staticmethod
    def straight_line_mode() -> str:
        """Enable straight line mode for smooth movements"""
        return "M2000"
    
    @staticmethod
    def absolute_mode() -> str:
        """Set absolute positioning"""
        return "G90"
    
    @staticmethod
    def relative_mode() -> str:
        """Set relative positioning"""
        return "G91"


class GCodeSender:
    """Sends G-code commands via serial transport"""
    
    def __init__(self, transport: ISerialTransport):
        self.transport = transport
        self.builder = GCodeBuilder()
    
    def send(self, command: str, wait_ok: bool = True) -> Optional[str]:
        """Send a G-code command"""
        return self.transport.send(command, wait_ok)
    
    def move(self, x: Optional[float] = None,
             y: Optional[float] = None,
             z: Optional[float] = None,
             feedrate: int = 3000,
             wait: bool = True) -> None:
        """Send move command and optionally wait"""
        cmd = self.builder.move(x, y, z, feedrate)
        self.send(cmd)
        if wait:
            self.send(self.builder.wait_for_move())
    
    def move_xyz(self, x: float, y: float, z: float, 
                 feedrate: int = 3000, wait: bool = True) -> None:
        """Move to XYZ position"""
        cmd = self.builder.move_xyz(x, y, z, feedrate)
        self.send(cmd)
        if wait:
            self.send(self.builder.wait_for_move())
    
    def move_z(self, z: float, feedrate: int = 3000, wait: bool = True) -> None:
        """Move Z only"""
        cmd = self.builder.move_z(z, feedrate)
        self.send(cmd)
        if wait:
            self.send(self.builder.wait_for_move())
    
    def move_xy(self, x: float, y: float, 
                feedrate: int = 3000, wait: bool = True) -> None:
        """Move XY only"""
        cmd = self.builder.move_xy(x, y, feedrate)
        self.send(cmd)
        if wait:
            self.send(self.builder.wait_for_move())
    
    def home(self) -> None:
        """Home the arm"""
        self.send(self.builder.home())
    
    def wait_for_move(self) -> None:
        """Wait for current move to complete"""
        self.send(self.builder.wait_for_move())
    
    def straight_line_mode(self) -> None:
        """Enable straight line mode for smooth movements"""
        self.send(self.builder.straight_line_mode())
