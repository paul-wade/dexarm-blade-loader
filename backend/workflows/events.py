"""
Events - State transition triggers
"""

from enum import Enum, auto
from dataclasses import dataclass
from typing import Any, Optional


class EventType(Enum):
    """Event types that trigger state transitions"""
    
    # User commands
    START_CYCLE = auto()
    PAUSE = auto()
    RESUME = auto()
    STOP = auto()
    
    # Internal events
    MOVE_COMPLETE = auto()
    ACTION_COMPLETE = auto()
    ERROR = auto()
    
    # Cycle events
    NEXT_HOOK = auto()
    CYCLE_COMPLETE = auto()


@dataclass
class Event:
    """Event with optional data payload"""
    type: EventType
    data: Optional[Any] = None
    
    @classmethod
    def start_cycle(cls) -> 'Event':
        return cls(EventType.START_CYCLE)
    
    @classmethod
    def pause(cls) -> 'Event':
        return cls(EventType.PAUSE)
    
    @classmethod
    def resume(cls) -> 'Event':
        return cls(EventType.RESUME)
    
    @classmethod
    def stop(cls) -> 'Event':
        return cls(EventType.STOP)
    
    @classmethod
    def move_complete(cls) -> 'Event':
        return cls(EventType.MOVE_COMPLETE)
    
    @classmethod
    def action_complete(cls) -> 'Event':
        return cls(EventType.ACTION_COMPLETE)
    
    @classmethod
    def error(cls, error_msg: str) -> 'Event':
        return cls(EventType.ERROR, data=error_msg)
    
    @classmethod
    def next_hook(cls, hook_index: int) -> 'Event':
        return cls(EventType.NEXT_HOOK, data=hook_index)
    
    @classmethod
    def cycle_complete(cls) -> 'Event':
        return cls(EventType.CYCLE_COMPLETE)
