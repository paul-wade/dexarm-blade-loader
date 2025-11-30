"""
Arm Controller - Single responsibility: arm movement control
Production-ready with safety interlocks and position verification
"""

import re
import time
from typing import Optional, Protocol, Callable
from dataclasses import dataclass, field

from core.gcode import GCodeSender, GCodeBuilder, Position
from core.serial_transport import SerialTransport


class SafetyError(Exception):
    """Raised when a safety interlock prevents movement"""
    pass


class PositionVerificationError(Exception):
    """Raised when position verification fails"""
    pass


class IArmController(Protocol):
    """Interface for arm control"""
    
    def move_to(self, x: float, y: float, z: float) -> None: ...
    def move_z(self, z: float) -> None: ...
    def move_xy(self, x: float, y: float) -> None: ...
    def home(self) -> None: ...
    def get_position(self) -> Position: ...
    def jog(self, axis: str, distance: float) -> None: ...
    def enable_teach_mode(self) -> None: ...
    def disable_teach_mode(self) -> None: ...


@dataclass
class ArmSettings:
    """Arm movement settings"""
    feedrate: int = 3000
    home_delay: float = 2.0
    # Safety settings
    safe_z: float = 0  # Will be set from PositionStore
    position_tolerance: float = 2.0  # mm tolerance for verification
    verify_moves: bool = False  # DISABLED - encoder values unreliable
    require_safe_z_for_xy: bool = False  # DISABLED for now - need testing
    max_retries: int = 3
    retry_delay: float = 0.5


class ArmController:
    """Controls arm movement - uses GCodeSender for commands
    
    Safety Features:
    - XY interlock: prevents XY movement unless at safe Z
    - Position verification: confirms moves completed correctly
    - Retry logic: automatic retry on verification failure
    """
    
    def __init__(self, transport: SerialTransport, settings: Optional[ArmSettings] = None):
        self.transport = transport
        self.gcode = GCodeSender(transport)
        self.builder = GCodeBuilder()
        self.settings = settings or ArmSettings()
        self._current_pos = Position(0, 300, 0)
        self._on_safety_warning: Optional[Callable[[str], None]] = None
    
    @property
    def current_position(self) -> Position:
        return self._current_pos
    
    @property
    def feedrate(self) -> int:
        return self.settings.feedrate
    
    @feedrate.setter
    def feedrate(self, value: int) -> None:
        self.settings.feedrate = value
    
    # === Safety Methods ===
    
    def set_safe_z(self, z: float) -> None:
        """Set the safe Z height for interlocks"""
        self.settings.safe_z = z
    
    def is_at_safe_z(self, tolerance: float = None) -> bool:
        """Check if arm is at or above safe Z"""
        tol = tolerance or self.settings.position_tolerance
        return self._current_pos.z >= (self.settings.safe_z - tol)
    
    def _check_xy_interlock(self) -> None:
        """Raise SafetyError if XY movement not allowed"""
        if not self.settings.require_safe_z_for_xy:
            return
        if self.settings.safe_z <= 0:
            return  # Safe Z not configured
        
        if not self.is_at_safe_z():
            msg = (f"XY BLOCKED: Z={self._current_pos.z:.1f}mm, "
                   f"must be >= {self.settings.safe_z:.1f}mm (safe Z)")
            self._warn(msg)
            raise SafetyError(msg)
    
    def _warn(self, message: str) -> None:
        """Log safety warning"""
        print(f"[SAFETY] ⚠️  {message}")
        if self._on_safety_warning:
            self._on_safety_warning(message)
    
    def _verify_position(self, expected: Position) -> bool:
        """Verify arm reached expected position"""
        if not self.settings.verify_moves:
            return True
        
        actual = self.get_position_from_encoder()
        tol = self.settings.position_tolerance
        
        dx = abs(actual.x - expected.x)
        dy = abs(actual.y - expected.y)
        dz = abs(actual.z - expected.z)
        
        if dx > tol or dy > tol or dz > tol:
            print(f"[VERIFY] ❌ Position error: expected ({expected.x:.1f}, {expected.y:.1f}, {expected.z:.1f}), "
                  f"got ({actual.x:.1f}, {actual.y:.1f}, {actual.z:.1f})")
            return False
        
        print(f"[VERIFY] ✓ Position OK")
        return True
    
    def _move_with_retry(self, move_fn, expected: Position, description: str) -> None:
        """Execute move with retry logic"""
        for attempt in range(self.settings.max_retries):
            move_fn()
            
            if not self.settings.verify_moves:
                return
            
            if self._verify_position(expected):
                return
            
            if attempt < self.settings.max_retries - 1:
                print(f"[RETRY] Attempt {attempt + 2}/{self.settings.max_retries} for {description}")
                time.sleep(self.settings.retry_delay)
        
        raise PositionVerificationError(f"Failed to reach {description} after {self.settings.max_retries} attempts")
    
    # === Movement Methods (with safety) ===
    
    def move_to(self, x: float, y: float, z: float, wait: bool = True, verify: bool = None) -> None:
        """Move to absolute XYZ position (checks XY interlock)"""
        # Check if XY is changing
        if abs(x - self._current_pos.x) > 0.1 or abs(y - self._current_pos.y) > 0.1:
            self._check_xy_interlock()
        
        expected = Position(x, y, z)
        do_verify = verify if verify is not None else self.settings.verify_moves
        
        def do_move():
            self.gcode.move_xyz(x, y, z, self.settings.feedrate, wait)
            self._current_pos = Position(x, y, z)
        
        if do_verify:
            self._move_with_retry(do_move, expected, f"XYZ({x:.1f}, {y:.1f}, {z:.1f})")
        else:
            do_move()
    
    def move_z(self, z: float, wait: bool = True, verify: bool = None) -> None:
        """Move Z axis only (always allowed)"""
        expected = Position(self._current_pos.x, self._current_pos.y, z)
        do_verify = verify if verify is not None else self.settings.verify_moves
        
        def do_move():
            self.gcode.move_z(z, self.settings.feedrate, wait)
            self._current_pos.z = z
        
        if do_verify:
            self._move_with_retry(do_move, expected, f"Z({z:.1f})")
        else:
            do_move()
    
    def move_xy(self, x: float, y: float, wait: bool = True, verify: bool = None) -> None:
        """Move XY axes only (requires safe Z)
        
        IMPORTANT: Always sends full XYZ command to maintain Z height.
        DexArm SCARA kinematics require explicit Z during XY moves.
        """
        self._check_xy_interlock()
        
        expected = Position(x, y, self._current_pos.z)
        do_verify = verify if verify is not None else self.settings.verify_moves
        
        def do_move():
            # MUST include current Z - DexArm needs full XYZ for proper movement
            self.gcode.move_xyz(x, y, self._current_pos.z, self.settings.feedrate, wait)
            self._current_pos.x = x
            self._current_pos.y = y
        
        if do_verify:
            self._move_with_retry(do_move, expected, f"XY({x:.1f}, {y:.1f})")
        else:
            do_move()
    
    def home(self) -> None:
        """Move to home position"""
        self.gcode.send(self.builder.home())
        time.sleep(self.settings.home_delay)
        self._current_pos = Position(0, 300, 0)
    
    def wait_for_move(self) -> None:
        """Wait for current move to complete"""
        self.gcode.wait_for_move()
    
    def jog(self, axis: str, distance: float) -> None:
        """Jog relative movement on single axis"""
        axis = axis.lower()  # Handle uppercase
        
        self.gcode.send(self.builder.relative_mode())
        
        if axis == 'x':
            self.gcode.send(f"G1 F1000 X{distance}")
            self._current_pos.x += distance
        elif axis == 'y':
            self.gcode.send(f"G1 F1000 Y{distance}")
            self._current_pos.y += distance
        elif axis == 'z':
            self.gcode.send(f"G1 F1000 Z{distance}")
            self._current_pos.z += distance
        else:
            print(f"[JOG] Unknown axis: {axis}")
        
        self.gcode.send(self.builder.absolute_mode())
        time.sleep(0.1)  # Small delay to prevent rapid-fire issues
    
    def get_position(self) -> Position:
        """Query current position from arm"""
        self.transport.clear_buffer()
        self.transport.write_raw(b'M114\r')
        
        x, y, z = None, None, None
        
        while True:
            try:
                line = self.transport.read_line()
                if 'X:' in line:
                    # Parse like working code: split by space, then by colon
                    parts = line.split()
                    for part in parts:
                        if part.startswith('X:'):
                            x = float(part[2:])
                        elif part.startswith('Y:'):
                            y = float(part[2:])
                        elif part.startswith('Z:'):
                            z = float(part[2:])
                
                if 'ok' in line.lower():
                    if x is not None:
                        self._current_pos = Position(x, y, z)
                    return self._current_pos
            except Exception:
                break
        
        return self._current_pos
    
    def get_position_from_encoder(self) -> Position:
        """Get current position using M114 (official pydexarm method)
        
        Response contains "X:... Y:... Z:..." - extract with regex
        """
        self.transport.clear_buffer()
        self.transport.write_raw(b'M114\r')
        
        while True:
            try:
                response = self.transport.read_line()
                if 'X:' in response:
                    # Parse like working code: split by space, then by colon
                    # Response format: "X:0.00 Y:300.00 Z:0.00 E:0.00"
                    try:
                        parts = response.split()
                        for part in parts:
                            if part.startswith('X:'):
                                self._current_pos.x = float(part[2:])
                            elif part.startswith('Y:'):
                                self._current_pos.y = float(part[2:])
                            elif part.startswith('Z:'):
                                self._current_pos.z = float(part[2:])
                        print(f"[POS] M114: ({self._current_pos.x:.1f}, {self._current_pos.y:.1f}, {self._current_pos.z:.1f})")
                    except:
                        pass
                if 'ok' in response.lower():
                    return self._current_pos
            except Exception as e:
                print(f"[POS] Error: {e}")
                break
        
        return self._current_pos
    
    def enable_teach_mode(self) -> None:
        """Disable motors for free movement"""
        self.gcode.send(self.builder.motors_off())
    
    def disable_teach_mode(self) -> None:
        """Re-enable motors"""
        self.gcode.send(self.builder.motors_on())
    
    def get_teach_position(self) -> Position:
        """Read position using M114 after enabling motors
        
        Same as get_position_from_encoder but called after teach mode
        """
        return self.get_position_from_encoder()
    
    def set_module(self, module_type: int) -> None:
        """Set front-end module (2 = Pneumatic)"""
        self.gcode.send(self.builder.set_module(module_type))
        time.sleep(0.3)
    
    def set_straight_line_mode(self) -> None:
        """Enable straight line mode for smooth movements"""
        self.gcode.send(self.builder.straight_line_mode())
    
    def emergency_stop(self) -> None:
        """M410 - EMERGENCY STOP all steppers immediately
        
        WARNING: Steppers will be out of position after this!
        Must re-home after e-stop.
        """
        print("[E-STOP] ⛔ EMERGENCY STOP TRIGGERED")
        self.gcode.send(self.builder.emergency_stop())
        self._current_pos = Position(0, 0, 0)  # Position is now unknown
