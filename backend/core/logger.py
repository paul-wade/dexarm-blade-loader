"""
Structured logging for DexArm Blade Loader.

Prefixes:
  ⚡ CRITICAL - Errors, failures
  ⚠️  WARN     - Warnings, unexpected behavior
  ✓  OK       - Success confirmations
  →  MOVE     - Movement commands
  ⟳  SYNC     - Position sync operations
  ⬡  SERIAL   - Raw serial I/O
  📍 POS      - Position readings
"""

from enum import Enum
from typing import Optional
from datetime import datetime


class LogLevel(Enum):
    CRITICAL = "⚡ CRITICAL"
    WARN = "⚠️  WARN    "
    OK = "✓  OK      "
    MOVE = "→  MOVE    "
    SYNC = "⟳  SYNC    "
    SERIAL = "⬡  SERIAL  "
    POS = "📍 POS     "
    INFO = "ℹ  INFO    "
    CYCLE = "🔄 CYCLE   "
    TEACH = "🎓 TEACH   "


def log(level: LogLevel, message: str, data: Optional[dict] = None):
    """Log a message with structured prefix."""
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    prefix = level.value
    
    line = f"[{timestamp}] {prefix} | {message}"
    if data:
        line += f" | {data}"
    
    print(line)


# Convenience functions
def log_critical(msg: str, data: Optional[dict] = None):
    log(LogLevel.CRITICAL, msg, data)

def log_warn(msg: str, data: Optional[dict] = None):
    log(LogLevel.WARN, msg, data)

def log_ok(msg: str, data: Optional[dict] = None):
    log(LogLevel.OK, msg, data)

def log_move(msg: str, data: Optional[dict] = None):
    log(LogLevel.MOVE, msg, data)

def log_sync(msg: str, data: Optional[dict] = None):
    log(LogLevel.SYNC, msg, data)

def log_serial(direction: str, data: str):
    """Log serial I/O. direction is '>>>' (send) or '<<<' (recv)"""
    log(LogLevel.SERIAL, f"{direction} {data}")

def log_pos(msg: str, data: Optional[dict] = None):
    log(LogLevel.POS, msg, data)

def log_info(msg: str, data: Optional[dict] = None):
    log(LogLevel.INFO, msg, data)

def log_cycle(msg: str, data: Optional[dict] = None):
    log(LogLevel.CYCLE, msg, data)

def log_teach(msg: str, data: Optional[dict] = None):
    log(LogLevel.TEACH, msg, data)
