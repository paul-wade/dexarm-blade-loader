"""
State Machine - Workflow orchestration engine
"""

from abc import ABC, abstractmethod
from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Optional, Callable, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from hardware.arm import ArmController
    from hardware.suction import SuctionController
    from core.position_store import PositionStore

from .events import Event, EventType


class StateResult(Enum):
    """Result of state execution"""
    SUCCESS = auto()
    FAILURE = auto()
    RUNNING = auto()
    PAUSED = auto()


@dataclass
class StateContext:
    """Shared context passed between states"""
    arm: 'ArmController'
    suction: 'SuctionController'
    positions: 'PositionStore'
    
    # Cycle state
    current_hook_index: int = 0
    total_hooks: int = 0
    
    # Status
    is_paused: bool = False
    is_stopped: bool = False
    error_message: Optional[str] = None
    
    # Callbacks
    on_status: Optional[Callable[[str], None]] = None
    on_progress: Optional[Callable[[int, int], None]] = None


class State(ABC):
    """Base class for all states"""
    
    name: str = "State"
    
    def __init__(self):
        self.retry_count = 0
        self.max_retries = 3
    
    @abstractmethod
    def on_enter(self, context: StateContext) -> StateResult:
        """Called when entering this state - perform the action"""
        pass
    
    def on_exit(self, context: StateContext) -> None:
        """Called when exiting this state - cleanup"""
        pass
    
    def on_error(self, context: StateContext, error: Exception) -> StateResult:
        """Handle error during execution"""
        self.retry_count += 1
        if self.retry_count < self.max_retries:
            return StateResult.RUNNING  # Will retry
        return StateResult.FAILURE
    
    def get_next_state(self, context: StateContext, result: StateResult) -> Optional['State']:
        """Determine next state based on result"""
        return None  # Override in subclass
    
    def log(self, context: StateContext, message: str) -> None:
        """Log status message"""
        print(f"[{self.name}] {message}")
        if context.on_status:
            context.on_status(f"[{self.name}] {message}")


class StateMachine:
    """Executes state transitions for workflows"""
    
    def __init__(self, context: StateContext):
        self.context = context
        self.current_state: Optional[State] = None
        self.is_running = False
        self._history: list[str] = []
    
    def start(self, initial_state: State) -> None:
        """Start the state machine with initial state"""
        self.is_running = True
        self.context.is_stopped = False
        self.context.is_paused = False
        self._transition_to(initial_state)
    
    def stop(self) -> None:
        """Stop the state machine"""
        self.context.is_stopped = True
        self.is_running = False
        if self.current_state:
            self.current_state.on_exit(self.context)
    
    def pause(self) -> None:
        """Pause the state machine"""
        self.context.is_paused = True
    
    def resume(self) -> None:
        """Resume the state machine"""
        self.context.is_paused = False
    
    def step(self) -> StateResult:
        """Execute one step of the state machine"""
        if not self.current_state or not self.is_running:
            return StateResult.SUCCESS
        
        if self.context.is_stopped:
            self.stop()
            return StateResult.FAILURE
        
        if self.context.is_paused:
            return StateResult.PAUSED
        
        try:
            result = self.current_state.on_enter(self.context)
        except Exception as e:
            print(f"[StateMachine] Error in {self.current_state.name}: {e}")
            result = self.current_state.on_error(self.context, e)
        
        if result == StateResult.SUCCESS:
            next_state = self.current_state.get_next_state(self.context, result)
            if next_state:
                self._transition_to(next_state)
                return StateResult.RUNNING
            else:
                self.is_running = False
                return StateResult.SUCCESS
        
        elif result == StateResult.FAILURE:
            self.context.error_message = f"Failed in state: {self.current_state.name}"
            self.is_running = False
            return StateResult.FAILURE
        
        return result
    
    def run_to_completion(self) -> StateResult:
        """Run the state machine until complete or error"""
        while self.is_running:
            if self.context.is_stopped:
                return StateResult.FAILURE
            
            # Check for pause
            if self.context.is_paused:
                import time
                time.sleep(0.1)
                continue
            
            result = self.step()
            if result in (StateResult.SUCCESS, StateResult.FAILURE):
                return result
        
        return StateResult.SUCCESS
    
    def _transition_to(self, state: State) -> None:
        """Transition to a new state"""
        if self.current_state:
            self.current_state.on_exit(self.context)
            self._history.append(self.current_state.name)
        
        self.current_state = state
        print(f"[StateMachine] → {state.name}")
    
    @property
    def state_name(self) -> str:
        """Get current state name"""
        return self.current_state.name if self.current_state else "None"
    
    @property
    def history(self) -> list[str]:
        """Get state transition history"""
        return self._history.copy()
