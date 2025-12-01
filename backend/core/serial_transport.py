"""
Serial Transport - Single responsibility: serial communication

Thread-safe: Uses lock to prevent concurrent access from multiple API requests.
"""

import serial
import serial.tools.list_ports
import time
import threading
from typing import Optional, Protocol
from dataclasses import dataclass
from .logger import log_serial, log_critical, log_ok


BAUD_RATE = 115200
DEFAULT_TIMEOUT = 2


class ISerialTransport(Protocol):
    """Interface for serial communication"""
    
    def connect(self, port: str) -> bool: ...
    def disconnect(self) -> None: ...
    def send(self, data: str, wait_ok: bool = True) -> Optional[str]: ...
    def read_line(self) -> str: ...
    def clear_buffer(self) -> None: ...
    @property
    def is_connected(self) -> bool: ...


@dataclass
class SerialConfig:
    baud_rate: int = BAUD_RATE
    timeout: float = DEFAULT_TIMEOUT
    connect_delay: float = 2.0


class SerialTransport:
    """
    Handles raw serial communication with the arm.
    
    Thread-safe: All send/read operations are protected by a lock.
    This prevents corruption when multiple API requests hit simultaneously.
    """
    
    def __init__(self, config: Optional[SerialConfig] = None):
        self.config = config or SerialConfig()
        self._serial: Optional[serial.Serial] = None
        self._connected = False
        self._lock = threading.Lock()  # Prevent concurrent serial access
    
    @staticmethod
    def list_ports() -> list[str]:
        """List available serial ports"""
        ports = serial.tools.list_ports.comports()
        return [port.device for port in ports]
    
    def connect(self, port: str) -> bool:
        """Connect to serial port"""
        try:
            self._serial = serial.Serial(
                port, 
                self.config.baud_rate, 
                timeout=self.config.timeout
            )
            time.sleep(self.config.connect_delay)
            self._connected = True
            return True
        except Exception as e:
            self._connected = False
            raise ConnectionError(f"Failed to connect: {e}")
    
    def disconnect(self) -> None:
        """Disconnect from serial port"""
        if self._serial:
            self._serial.close()
            self._serial = None
        self._connected = False
    
    def send(self, data: str, wait_ok: bool = True) -> Optional[str]:
        """
        Send data and optionally wait for 'ok' response.
        
        Thread-safe: Acquires lock before sending to prevent interleaved commands.
        """
        if not self._serial or not self._connected:
            raise ConnectionError("Not connected")
        
        with self._lock:  # CRITICAL: Serialize all serial access
            log_serial(">>>", data)
            self._serial.write(f"{data}\r".encode())
            
            if not wait_ok:
                self._serial.reset_input_buffer()
                return None
            
            return self._wait_for_ok()
    
    def send_emergency(self, data: str) -> None:
        """
        Send emergency command WITHOUT waiting for lock.
        
        USE ONLY FOR EMERGENCY STOP (M410).
        This will interrupt any in-progress command.
        """
        if not self._serial or not self._connected:
            return
        
        log_serial("!!! EMERGENCY", data)
        try:
            self._serial.write(f"{data}\r".encode())
            self._serial.reset_input_buffer()  # Clear any pending responses
        except:
            pass  # Best effort - don't raise on emergency
    
    def _wait_for_ok(self, timeout: float = 10.0) -> str:
        """
        Wait for 'ok' response from device with timeout.
        
        Collects ALL response lines until 'ok' is found, returns them joined.
        This handles commands like M114 where data comes before 'ok':
          X:100.00 Y:250.00 Z:50.00 E:0.00
          ok
        """
        start = time.time()
        lines = []
        while (time.time() - start) < timeout:
            response = self._serial.readline().decode().strip()
            if response:
                lines.append(response)
                log_serial("<<<", response)
                if 'ok' in response.lower():
                    return '\n'.join(lines)
            else:
                time.sleep(0.05)
        # Timeout - clear buffer and raise
        self._serial.reset_input_buffer()
        log_critical(f"Timeout waiting for 'ok' after {timeout}s")
        raise TimeoutError(f"Timeout waiting for 'ok' after {timeout}s")
    
    def read_line(self) -> str:
        """Read a single line from serial"""
        if not self._serial:
            raise ConnectionError("Not connected")
        return self._serial.readline().decode().strip()
    
    def read_until_ok(self) -> list[str]:
        """Read all lines until 'ok' received"""
        lines = []
        while True:
            line = self.read_line()
            lines.append(line)
            if 'ok' in line.lower():
                break
        return lines
    
    def clear_buffer(self) -> None:
        """Clear input buffer"""
        if self._serial:
            self._serial.reset_input_buffer()
    
    def write_raw(self, data: bytes) -> None:
        """Write raw bytes"""
        if not self._serial:
            raise ConnectionError("Not connected")
        self._serial.write(data)
    
    @property
    def is_connected(self) -> bool:
        return self._connected
    
    @property
    def in_waiting(self) -> int:
        """Bytes waiting in input buffer"""
        return self._serial.in_waiting if self._serial else 0
