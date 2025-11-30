"""
Command execution layer.

Task 2.1: Command Queue

Provides:
- CommandQueue: Ordered, auditable command buffer
- CommandResult: Execution result with timestamp
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import List, Union, TYPE_CHECKING

from .types import (
    Command,
    MoveCommand,
    WaitCommand,
    HomeCommand,
    SuctionCommand,
    DelayCommand,
    SetModuleCommand,
    GetPositionCommand,
    MotorsCommand,
    EmergencyStopCommand,
)

if TYPE_CHECKING:
    from .transport import Transport


# Union of all command types for type checking
AnyCommand = Union[
    MoveCommand,
    WaitCommand,
    HomeCommand,
    SuctionCommand,
    DelayCommand,
    SetModuleCommand,
    GetPositionCommand,
    MotorsCommand,
    EmergencyStopCommand,
]


@dataclass
class CommandResult:
    """
    Result of executing a command.
    
    Immutable record for audit trail.
    """
    command: AnyCommand
    gcode: str
    response: str
    timestamp: datetime
    success: bool
    
    def __str__(self) -> str:
        status = "✓" if self.success else "✗"
        return f"[{self.timestamp:%H:%M:%S}] {status} {self.gcode} → {self.response}"


class CommandQueue:
    """
    Ordered, auditable command queue.
    
    Features:
    - Enqueue commands for batch execution
    - Execute all with transport
    - Full history for debugging/audit
    """
    
    def __init__(self):
        self._pending: List[AnyCommand] = []
        self._history: List[CommandResult] = []
    
    def enqueue(self, command: AnyCommand) -> None:
        """Add a command to the queue."""
        self._pending.append(command)
    
    def enqueue_many(self, commands: List[AnyCommand]) -> None:
        """Add multiple commands to the queue."""
        self._pending.extend(commands)
    
    def pending_count(self) -> int:
        """Number of commands waiting to execute."""
        return len(self._pending)
    
    def execute_all(self, transport: "Transport") -> List[CommandResult]:
        """
        Execute all pending commands via transport.
        
        Commands are executed in order. Each result is recorded in history.
        Queue is cleared after execution.
        
        Returns list of results for this batch.
        """
        batch_results: List[CommandResult] = []
        
        for command in self._pending:
            result = self._execute_one(command, transport)
            self._history.append(result)
            batch_results.append(result)
        
        self._pending.clear()
        return batch_results
    
    def _execute_one(self, command: AnyCommand, transport: "Transport") -> CommandResult:
        """Execute a single command and return result."""
        gcode = command.to_gcode()
        timestamp = datetime.now()
        
        try:
            response = transport.send(gcode)
            success = "ok" in response.lower()
        except Exception as e:
            response = f"ERROR: {e}"
            success = False
        
        return CommandResult(
            command=command,
            gcode=gcode,
            response=response,
            timestamp=timestamp,
            success=success,
        )
    
    def execute_immediate(self, command: AnyCommand, transport: "Transport") -> CommandResult:
        """
        Execute a single command immediately, bypassing queue.
        
        Still recorded in history.
        """
        result = self._execute_one(command, transport)
        self._history.append(result)
        return result
    
    def get_history(self, limit: int | None = None) -> List[CommandResult]:
        """
        Get execution history.
        
        Args:
            limit: Optional max number of recent entries to return.
        """
        if limit is None:
            return list(self._history)
        return list(self._history[-limit:])
    
    def clear(self) -> None:
        """Clear pending commands (preserves history)."""
        self._pending.clear()
    
    def clear_history(self) -> None:
        """Clear execution history."""
        self._history.clear()
    
    def get_pending(self) -> List[AnyCommand]:
        """Get list of pending commands (copy)."""
        return list(self._pending)
    
    def get_last_result(self) -> CommandResult | None:
        """Get most recent execution result."""
        return self._history[-1] if self._history else None
    
    def print_history(self, limit: int = 20) -> None:
        """Print recent history to console (for debugging)."""
        for result in self.get_history(limit):
            print(result)
