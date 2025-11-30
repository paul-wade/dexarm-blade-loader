"""
Suction Controller - Single responsibility: suction pump control
"""

import time
from typing import Protocol
from dataclasses import dataclass

from core.gcode import GCodeSender, GCodeBuilder
from core.serial_transport import SerialTransport


class ISuctionController(Protocol):
    """Interface for suction control"""
    
    def grab(self) -> None: ...
    def release(self) -> None: ...
    def off(self) -> None: ...


@dataclass
class SuctionSettings:
    """Suction timing settings"""
    grab_delay: float = 0.5      # Time to let suction build
    release_delay: float = 0.3   # Time to release air (matches working code)


class SuctionController:
    """Controls suction pump
    
    Commands (for suction cup):
    - M1000: Pump IN (grab)
    - M1001: Pump OUT (blow air to release)
    - M1002: Release air (neutral)
    - M1003: Stop pump
    """
    
    def __init__(self, transport: SerialTransport, settings: SuctionSettings = None):
        self.transport = transport
        self.gcode = GCodeSender(transport)
        self.builder = GCodeBuilder()
        self.settings = settings or SuctionSettings()
        self._is_active = False
    
    @property
    def is_active(self) -> bool:
        return self._is_active
    
    def grab(self) -> None:
        """M1000 - Pump IN to grab object"""
        print("[SUCTION] Grab (M1000 pump in)")
        self.gcode.send(self.builder.suction_on())
        time.sleep(self.settings.grab_delay)
        self._is_active = True
    
    def release(self) -> None:
        """Release sequence: release air → stop (matches working code)"""
        print("[SUCTION] Release (M1002 release → M1003 stop)")
        # Step 1: Release air pressure
        self.gcode.send(self.builder.suction_release())  # M1002
        time.sleep(0.5)  # Working code uses 0.5s here
        
        # Step 2: Stop pump
        self.gcode.send(self.builder.suction_off())  # M1003
        time.sleep(0.2)  # Working code waits 0.2s after stop before lifting
        self._is_active = False
    
    def off(self) -> None:
        """M1003 - Stop pump immediately"""
        self.gcode.send(self.builder.suction_off())
        self._is_active = False
    
    def on(self) -> None:
        """M1000 - Turn on suction with delay for pump to start"""
        self.gcode.send(self.builder.suction_on())
        time.sleep(0.3)  # Working code waits 0.3s after M1000 before lowering
        self._is_active = True
    
    def blow(self) -> None:
        """M1001 - Blow air out (manual control)"""
        self.gcode.send(self.builder.suction_blow())
    
    def neutralize(self) -> None:
        """M1002 - Release air pressure to neutral"""
        self.gcode.send(self.builder.suction_release())
