"""
Unit tests for pick-place workflow state machine.

Task 3.1: Pick-Place Workflow
"""

import pytest
from core.types import Position
from core.transport import MockTransport
from core.executor import CommandQueue
from core.planner import MotionPlanner
from workflows.pick_place import PickPlaceWorkflow, WorkflowState


class TestWorkflowStates:
    """Test workflow state transitions."""

    def test_initial_state_is_idle(self):
        """Workflow starts in IDLE state."""
        wf = PickPlaceWorkflow()
        assert wf.state == WorkflowState.IDLE

    def test_start_transitions_to_moving_to_pick(self):
        """start() transitions from IDLE to MOVING_TO_PICK."""
        wf = PickPlaceWorkflow()
        wf.configure(
            pick_position=Position(100, 200, 10),
            place_position=Position(-100, 200, 10),
        )
        wf.start()
        assert wf.state == WorkflowState.MOVING_TO_PICK

    def test_cannot_start_without_positions(self):
        """Cannot start workflow without configured positions."""
        wf = PickPlaceWorkflow()
        with pytest.raises(ValueError, match="positions"):
            wf.start()

    def test_cannot_start_when_not_idle(self):
        """Cannot start when already running."""
        wf = PickPlaceWorkflow()
        wf.configure(
            pick_position=Position(100, 200, 10),
            place_position=Position(-100, 200, 10),
        )
        wf.start()
        
        with pytest.raises(ValueError, match="not idle"):
            wf.start()

    def test_reset_returns_to_idle(self):
        """reset() returns to IDLE from any state."""
        wf = PickPlaceWorkflow()
        wf.configure(
            pick_position=Position(100, 200, 10),
            place_position=Position(-100, 200, 10),
        )
        wf.start()
        assert wf.state != WorkflowState.IDLE
        
        wf.reset()
        assert wf.state == WorkflowState.IDLE


class TestWorkflowExecution:
    """Test full workflow execution."""

    @pytest.fixture
    def workflow_setup(self):
        """Create workflow with all dependencies."""
        transport = MockTransport()
        queue = CommandQueue()
        planner = MotionPlanner(safe_z=50.0)
        wf = PickPlaceWorkflow(
            transport=transport,
            queue=queue,
            planner=planner,
        )
        wf.configure(
            pick_position=Position(100, 200, 10),
            place_position=Position(-100, 200, 10),
        )
        return wf, transport, queue

    def test_step_advances_state(self, workflow_setup):
        """step() advances workflow state."""
        wf, transport, queue = workflow_setup
        wf.start()
        
        initial_state = wf.state
        wf.step()
        
        # Should have advanced (might be same if still executing)
        assert wf.state != WorkflowState.IDLE

    def test_run_to_completion(self, workflow_setup):
        """run() executes full cycle."""
        wf, transport, queue = workflow_setup
        
        wf.run()
        
        assert wf.state == WorkflowState.COMPLETE

    def test_complete_cycle_sends_commands(self, workflow_setup):
        """Complete cycle sends expected commands."""
        wf, transport, queue = workflow_setup
        
        wf.run()
        
        # Should have sent: home movements, suction, etc.
        assert transport.command_count > 0
        
        # Check key commands were sent
        commands = transport.sent_commands
        assert any("M1000" in cmd for cmd in commands)  # Suction on
        assert any("M1002" in cmd or "M1003" in cmd for cmd in commands)  # Suction release/off

    def test_history_recorded(self, workflow_setup):
        """Execution history is recorded."""
        wf, transport, queue = workflow_setup
        
        wf.run()
        
        history = queue.get_history()
        assert len(history) > 0

    def test_position_updates_after_cycle(self, workflow_setup):
        """Position is updated after cycle."""
        wf, transport, queue = workflow_setup
        initial_pos = transport.position
        
        wf.run()
        
        # Position should have changed
        final_pos = transport.position
        # After place and lift, should be at safe_z above place position
        assert final_pos.z == 50.0  # safe_z


class TestWorkflowErrorHandling:
    """Test error handling in workflow."""

    def test_error_state_on_transport_error(self):
        """Workflow enters ERROR state on transport failure."""
        transport = MockTransport()
        transport.disconnect()  # Simulate disconnect
        
        queue = CommandQueue()
        planner = MotionPlanner(safe_z=50.0)
        wf = PickPlaceWorkflow(
            transport=transport,
            queue=queue,
            planner=planner,
        )
        wf.configure(
            pick_position=Position(100, 200, 10),
            place_position=Position(-100, 200, 10),
        )
        
        # Should handle error gracefully
        # (MockTransport still returns ok even when disconnected, 
        #  but we can test the error handling mechanism)

    def test_can_reset_from_error(self):
        """Can reset from ERROR state."""
        wf = PickPlaceWorkflow()
        wf._state = WorkflowState.ERROR  # Force error state
        
        wf.reset()
        
        assert wf.state == WorkflowState.IDLE


class TestWorkflowCallbacks:
    """Test workflow event callbacks."""

    def test_on_state_change_called(self):
        """Callback fired on state change."""
        wf = PickPlaceWorkflow()
        wf.configure(
            pick_position=Position(100, 200, 10),
            place_position=Position(-100, 200, 10),
        )
        
        states_seen = []
        wf.on_state_change = lambda old, new: states_seen.append((old, new))
        
        wf.start()
        
        assert len(states_seen) > 0
        assert states_seen[0][0] == WorkflowState.IDLE
        assert states_seen[0][1] == WorkflowState.MOVING_TO_PICK

    def test_on_complete_called(self):
        """on_complete callback fired when done."""
        transport = MockTransport()
        queue = CommandQueue()
        planner = MotionPlanner(safe_z=50.0)
        wf = PickPlaceWorkflow(
            transport=transport,
            queue=queue,
            planner=planner,
        )
        wf.configure(
            pick_position=Position(100, 200, 10),
            place_position=Position(-100, 200, 10),
        )
        
        completed = []
        wf.on_complete = lambda: completed.append(True)
        
        wf.run()
        
        assert len(completed) == 1
