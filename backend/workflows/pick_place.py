"""
Pick-Place Workflow State Machine.

Task 3.1: Pick-Place Workflow

A state machine that orchestrates the complete pick-and-place cycle:
1. Move to pick position (safely)
2. Activate suction
3. Lower to pick
4. Lift with blade
5. Move to place position (safely)
6. Lower to place
7. Release suction
8. Lift and complete
"""

from __future__ import annotations

from enum import Enum, auto
from typing import Callable, Optional, TYPE_CHECKING

from core.types import Position, HomeCommand
from core.planner import MotionPlanner

if TYPE_CHECKING:
    from core.transport import Transport
    from core.executor import CommandQueue


class WorkflowState(Enum):
    """States in the pick-place workflow."""
    IDLE = auto()
    MOVING_TO_PICK = auto()
    LOWERING_TO_PICK = auto()
    ACTIVATING_SUCTION = auto()
    LIFTING_FROM_PICK = auto()
    MOVING_TO_PLACE = auto()
    LOWERING_TO_PLACE = auto()
    RELEASING = auto()
    LIFTING_FROM_PLACE = auto()
    COMPLETE = auto()
    ERROR = auto()


class PickPlaceWorkflow:
    """
    State machine for pick-and-place operations.
    
    Usage:
        wf = PickPlaceWorkflow(transport, queue, planner)
        wf.configure(pick_pos, place_pos)
        wf.run()  # Blocking, runs to completion
        
        # Or step-by-step:
        wf.start()
        while wf.state != WorkflowState.COMPLETE:
            wf.step()
    """
    
    def __init__(
        self,
        transport: Optional["Transport"] = None,
        queue: Optional["CommandQueue"] = None,
        planner: Optional[MotionPlanner] = None,
    ):
        self._transport = transport
        self._queue = queue
        self._planner = planner or MotionPlanner(safe_z=50.0)
        
        self._state = WorkflowState.IDLE
        self._pick_position: Optional[Position] = None
        self._place_position: Optional[Position] = None
        self._current_position: Position = Position(0, 300, 0)  # Assume home
        
        # Callbacks
        self.on_state_change: Optional[Callable[[WorkflowState, WorkflowState], None]] = None
        self.on_complete: Optional[Callable[[], None]] = None
        self.on_error: Optional[Callable[[str], None]] = None
    
    @property
    def state(self) -> WorkflowState:
        """Current workflow state."""
        return self._state
    
    def _set_state(self, new_state: WorkflowState) -> None:
        """Set state and fire callback."""
        old_state = self._state
        self._state = new_state
        if self.on_state_change:
            self.on_state_change(old_state, new_state)
    
    def configure(
        self,
        pick_position: Position,
        place_position: Position,
        current_position: Optional[Position] = None,
    ) -> None:
        """
        Configure the workflow positions.
        
        Must be called before start().
        """
        self._pick_position = pick_position
        self._place_position = place_position
        if current_position:
            self._current_position = current_position
    
    def start(self) -> None:
        """
        Start the workflow.
        
        Transitions from IDLE to MOVING_TO_PICK.
        Raises ValueError if not configured or not idle.
        """
        if self._state != WorkflowState.IDLE:
            raise ValueError("Cannot start: workflow is not idle")
        
        if self._pick_position is None or self._place_position is None:
            raise ValueError("Cannot start: positions not configured")
        
        self._set_state(WorkflowState.MOVING_TO_PICK)
    
    def reset(self) -> None:
        """Reset workflow to IDLE state."""
        self._set_state(WorkflowState.IDLE)
    
    def step(self) -> WorkflowState:
        """
        Execute one step of the workflow.
        
        Returns the new state after the step.
        """
        if self._state == WorkflowState.IDLE:
            return self._state
        
        if self._state == WorkflowState.COMPLETE:
            return self._state
        
        if self._state == WorkflowState.ERROR:
            return self._state
        
        try:
            self._execute_current_state()
            self._advance_state()
        except Exception as e:
            self._handle_error(str(e))
        
        return self._state
    
    def run(self) -> None:
        """
        Run the complete workflow.
        
        Blocking call - returns when complete or error.
        """
        self.start()
        
        while self._state not in (WorkflowState.COMPLETE, WorkflowState.ERROR):
            self.step()
        
        if self._state == WorkflowState.COMPLETE and self.on_complete:
            self.on_complete()
    
    def _execute_current_state(self) -> None:
        """Execute commands for current state."""
        if self._transport is None or self._queue is None:
            return  # No-op if no transport (for state testing)
        
        if self._state == WorkflowState.MOVING_TO_PICK:
            self._execute_move_to_pick()
        
        elif self._state == WorkflowState.LOWERING_TO_PICK:
            self._execute_lower_to_pick()
        
        elif self._state == WorkflowState.ACTIVATING_SUCTION:
            self._execute_activate_suction()
        
        elif self._state == WorkflowState.LIFTING_FROM_PICK:
            self._execute_lift_from_pick()
        
        elif self._state == WorkflowState.MOVING_TO_PLACE:
            self._execute_move_to_place()
        
        elif self._state == WorkflowState.LOWERING_TO_PLACE:
            self._execute_lower_to_place()
        
        elif self._state == WorkflowState.RELEASING:
            self._execute_release()
        
        elif self._state == WorkflowState.LIFTING_FROM_PLACE:
            self._execute_lift_from_place()
    
    def _advance_state(self) -> None:
        """Advance to next state."""
        transitions = {
            WorkflowState.MOVING_TO_PICK: WorkflowState.LOWERING_TO_PICK,
            WorkflowState.LOWERING_TO_PICK: WorkflowState.ACTIVATING_SUCTION,
            WorkflowState.ACTIVATING_SUCTION: WorkflowState.LIFTING_FROM_PICK,
            WorkflowState.LIFTING_FROM_PICK: WorkflowState.MOVING_TO_PLACE,
            WorkflowState.MOVING_TO_PLACE: WorkflowState.LOWERING_TO_PLACE,
            WorkflowState.LOWERING_TO_PLACE: WorkflowState.RELEASING,
            WorkflowState.RELEASING: WorkflowState.LIFTING_FROM_PLACE,
            WorkflowState.LIFTING_FROM_PLACE: WorkflowState.COMPLETE,
        }
        
        if self._state in transitions:
            self._set_state(transitions[self._state])
    
    def _handle_error(self, message: str) -> None:
        """Handle error during execution."""
        self._set_state(WorkflowState.ERROR)
        if self.on_error:
            self.on_error(message)
    
    # ==========================================================================
    # State execution methods
    # ==========================================================================
    
    def _execute_move_to_pick(self) -> None:
        """Move safely to above pick position."""
        assert self._pick_position is not None
        
        above_pick = self._pick_position.with_z(self._planner.safe_z)
        commands = self._planner.plan_safe_move(self._current_position, above_pick)
        
        self._queue.enqueue_many(commands)
        self._queue.execute_all(self._transport)
        
        self._current_position = above_pick
    
    def _execute_lower_to_pick(self) -> None:
        """Lower to pick position."""
        assert self._pick_position is not None
        
        from core.types import MoveCommand, WaitCommand
        
        self._queue.enqueue(MoveCommand(z=self._pick_position.z, feedrate=self._planner.feedrate))
        self._queue.enqueue(WaitCommand())
        self._queue.execute_all(self._transport)
        
        self._current_position = self._pick_position
    
    def _execute_activate_suction(self) -> None:
        """Turn on suction and wait for vacuum."""
        from core.types import SuctionCommand, DelayCommand
        
        self._queue.enqueue(SuctionCommand("on"))
        self._queue.enqueue(DelayCommand(milliseconds=200))
        self._queue.execute_all(self._transport)
    
    def _execute_lift_from_pick(self) -> None:
        """Lift to safe height with blade."""
        from core.types import MoveCommand, WaitCommand
        
        self._queue.enqueue(MoveCommand(z=self._planner.safe_z, feedrate=self._planner.feedrate))
        self._queue.enqueue(WaitCommand())
        self._queue.execute_all(self._transport)
        
        self._current_position = self._current_position.with_z(self._planner.safe_z)
    
    def _execute_move_to_place(self) -> None:
        """Move safely to above place position."""
        assert self._place_position is not None
        
        above_place = self._place_position.with_z(self._planner.safe_z)
        commands = self._planner.plan_safe_move(self._current_position, above_place)
        
        self._queue.enqueue_many(commands)
        self._queue.execute_all(self._transport)
        
        self._current_position = above_place
    
    def _execute_lower_to_place(self) -> None:
        """Lower to place position."""
        assert self._place_position is not None
        
        from core.types import MoveCommand, WaitCommand
        
        self._queue.enqueue(MoveCommand(z=self._place_position.z, feedrate=self._planner.feedrate))
        self._queue.enqueue(WaitCommand())
        self._queue.execute_all(self._transport)
        
        self._current_position = self._place_position
    
    def _execute_release(self) -> None:
        """Release suction."""
        from core.types import SuctionCommand, DelayCommand
        
        self._queue.enqueue(SuctionCommand("release"))
        self._queue.enqueue(DelayCommand(milliseconds=100))
        self._queue.enqueue(SuctionCommand("off"))
        self._queue.execute_all(self._transport)
    
    def _execute_lift_from_place(self) -> None:
        """Lift to safe height after placing."""
        from core.types import MoveCommand, WaitCommand
        
        self._queue.enqueue(MoveCommand(z=self._planner.safe_z, feedrate=self._planner.feedrate))
        self._queue.enqueue(WaitCommand())
        self._queue.execute_all(self._transport)
        
        self._current_position = self._current_position.with_z(self._planner.safe_z)
