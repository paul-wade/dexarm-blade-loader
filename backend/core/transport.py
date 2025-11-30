"""
Transport layer - handles communication with DexArm.

Task 2.2: Transport Abstraction

Provides:
- Transport protocol (interface)
- MockTransport for testing
- (SerialTransport in separate file for production)
"""

from __future__ import annotations

import re
from typing import Protocol, List, Optional

from .types import Position


class Transport(Protocol):
    """Protocol for DexArm communication."""
    
    def send(self, gcode: str) -> str:
        """
        Send G-code command and return response.
        
        Returns 'ok' on success, or response data for queries.
        """
        ...
    
    @property
    def is_connected(self) -> bool:
        """Check if transport is connected."""
        ...


class MockTransport:
    """
    Mock transport for testing without hardware.
    
    Simulates DexArm responses and tracks position.
    """
    
    def __init__(self):
        self.sent_commands: List[str] = []
        self.position: Position = Position(0, 300, 0)  # Home position
        self._connected: bool = True
        self._suction_state: str = "off"
    
    @property
    def command_count(self) -> int:
        """Number of commands sent."""
        return len(self.sent_commands)
    
    def send(self, gcode: str) -> str:
        """
        Simulate sending a command.
        
        Tracks command and simulates position changes.
        """
        self.sent_commands.append(gcode)
        
        # Simulate responses for different commands
        if gcode == "M1112":
            # Home command
            self.position = Position(0, 300, 0)
            return "ok"
        
        elif gcode.startswith("G1"):
            # Move command - parse and update position
            self._simulate_move(gcode)
            return "ok"
        
        elif gcode == "M114":
            # Position query - format matches real arm: data line then ok
            return f"X:{self.position.x:.2f} Y:{self.position.y:.2f} Z:{self.position.z:.2f} E:0.00\nok"
        
        elif gcode == "M400":
            # Wait - no-op in mock
            return "ok"
        
        elif gcode in ("M1000", "M1001", "M1002", "M1003"):
            # Suction commands
            states = {
                "M1000": "on",
                "M1001": "blow",
                "M1002": "release",
                "M1003": "off",
            }
            self._suction_state = states[gcode]
            return "ok"
        
        elif gcode.startswith("G4"):
            # Delay - no-op in mock
            return "ok"
        
        elif gcode.startswith("M888"):
            # Module select
            return "ok"
        
        elif gcode in ("M17", "M84"):
            # Motors on/off
            return "ok"
        
        elif gcode == "M893":
            # Read raw encoder values
            return f"M894 X{int(self.position.x*100)} Y{int(self.position.y*100)} Z{int(self.position.z*100)}\nok"
        
        elif gcode == "M895":
            # Read encoder and convert to Cartesian - this is what we use for teach mode
            return f"X:{self.position.x:.2f} Y:{self.position.y:.2f} Z:{self.position.z:.2f}\nok"
        
        elif gcode == "M410":
            # Emergency stop
            return "ok"
        
        # Default: return ok for unknown commands
        return "ok"
    
    def _simulate_move(self, gcode: str) -> None:
        """Parse G1 command and update simulated position."""
        x = self.position.x
        y = self.position.y
        z = self.position.z
        
        # Parse X, Y, Z values from G-code
        x_match = re.search(r'X([-\d.]+)', gcode)
        y_match = re.search(r'Y([-\d.]+)', gcode)
        z_match = re.search(r'Z([-\d.]+)', gcode)
        
        if x_match:
            x = float(x_match.group(1))
        if y_match:
            y = float(y_match.group(1))
        if z_match:
            z = float(z_match.group(1))
        
        self.position = Position(x, y, z)
    
    @property
    def is_connected(self) -> bool:
        """Mock is always connected."""
        return self._connected
    
    def disconnect(self) -> None:
        """Simulate disconnection (for testing error handling)."""
        self._connected = False
    
    def reconnect(self) -> None:
        """Simulate reconnection."""
        self._connected = True
    
    def get_suction_state(self) -> str:
        """Get simulated suction state."""
        return self._suction_state
    
    def clear_history(self) -> None:
        """Clear sent commands history."""
        self.sent_commands.clear()
