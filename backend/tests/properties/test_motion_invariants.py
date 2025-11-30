"""
Property-Based Tests for Motion Invariants.

Task 1.2: Motion Planner PBT

These tests verify that motion planning satisfies safety invariants
for ANY valid input, not just hand-picked examples.
"""

import math
import pytest
from hypothesis import given, assume, settings, HealthCheck
from hypothesis import strategies as st

from core.types import (
    MoveCommand,
    Position,
    WaitCommand,
    WorkspaceLimits,
    DEFAULT_WORKSPACE,
)
from core.planner import (
    MotionPlanner,
    verify_safe_move_invariant,
    verify_wait_after_moves,
)


# =============================================================================
# Hypothesis Strategies
# =============================================================================


@st.composite
def valid_position(draw: st.DrawFn) -> Position:
    """Generate a position within the DexArm workspace."""
    ws = DEFAULT_WORKSPACE
    
    # Generate using polar coordinates to respect reach constraint
    angle = draw(st.floats(min_value=-math.pi/2, max_value=math.pi/2))
    reach = draw(st.floats(min_value=ws.y_min, max_value=min(ws.max_reach, ws.y_max)))
    
    x = reach * math.sin(angle)
    y = reach * math.cos(angle)
    z = draw(st.floats(min_value=ws.z_min, max_value=ws.z_max))
    
    # Clamp to workspace
    x = max(ws.x_min, min(ws.x_max, x))
    y = max(ws.y_min, min(ws.y_max, y))
    
    pos = Position(x=x, y=y, z=z)
    
    # Verify valid
    valid, _ = ws.validate(pos)
    assume(valid)
    
    return pos


safe_z_strategy = st.floats(min_value=10.0, max_value=100.0)


# =============================================================================
# INV-M1: Safe Move Lifts Z First
# =============================================================================


class TestSafeMoveLiftsFirst:
    """
    INV-M1: A safe move from below safe_z must lift Z before any XY motion.
    """

    @given(safe_z=safe_z_strategy, target=valid_position())
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_safe_move_lifts_before_xy(self, safe_z: float, target: Position):
        """Safe moves must lift Z before XY when starting below safe_z."""
        # Current position below safe_z with different XY than target
        current = Position(
            x=target.x + 50 if target.x < 100 else target.x - 50,
            y=target.y,
            z=safe_z - 20,
        )
        
        valid, _ = DEFAULT_WORKSPACE.validate(current)
        assume(valid)
        
        planner = MotionPlanner(safe_z=safe_z)
        commands = planner.plan_safe_move(current, target)
        
        passed, msg = verify_safe_move_invariant(commands, current, safe_z)
        assert passed, f"INV-M1 violated: {msg}"

    @given(safe_z=safe_z_strategy, target=valid_position())
    @settings(max_examples=100)
    def test_safe_move_from_above_safe_z(self, safe_z: float, target: Position):
        """Safe moves from above safe_z are still valid."""
        current = Position(x=0, y=250, z=safe_z + 10)
        
        planner = MotionPlanner(safe_z=safe_z)
        commands = planner.plan_safe_move(current, target)
        
        passed, msg = verify_safe_move_invariant(commands, current, safe_z)
        assert passed, f"INV-M1 violated from above safe_z: {msg}"


# =============================================================================
# INV-M3: Wait After Every Move
# =============================================================================


class TestWaitAfterMoves:
    """
    INV-M3: Every move command must be followed by wait before next move.
    """

    @given(safe_z=safe_z_strategy, current=valid_position(), target=valid_position())
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_safe_move_has_waits(self, safe_z: float, current: Position, target: Position):
        """Safe move sequences have wait after each move."""
        planner = MotionPlanner(safe_z=safe_z)
        commands = planner.plan_safe_move(current, target)
        
        passed, msg = verify_wait_after_moves(commands)
        assert passed, f"INV-M3 violated: {msg}"

    @given(target=valid_position())
    @settings(max_examples=100)
    def test_direct_move_has_wait(self, target: Position):
        """Direct move has wait command."""
        planner = MotionPlanner(safe_z=50.0)
        commands = planner.plan_direct_move(target)
        
        passed, msg = verify_wait_after_moves(commands)
        assert passed, f"INV-M3 violated: {msg}"


# =============================================================================
# INV-M4: Positions Within Workspace
# =============================================================================


class TestWorkspaceValidation:
    """
    INV-M4: Planner rejects positions outside workspace.
    """

    def test_rejects_x_out_of_range(self):
        """Planner rejects X outside workspace."""
        planner = MotionPlanner(safe_z=50.0)
        invalid_target = Position(x=350, y=250, z=50)  # Above x_max=300
        
        with pytest.raises(ValueError, match="out of range"):
            planner.plan_direct_move(invalid_target)

    def test_rejects_y_too_low(self):
        """Planner rejects Y below minimum."""
        planner = MotionPlanner(safe_z=50.0)
        invalid_target = Position(x=0, y=50, z=50)
        
        with pytest.raises(ValueError, match="out of range"):
            planner.plan_direct_move(invalid_target)

    def test_rejects_reach_exceeded(self):
        """Planner rejects positions beyond reach."""
        planner = MotionPlanner(safe_z=50.0)
        invalid_target = Position(x=300, y=350, z=50)  # reach ~460mm > 400mm
        
        with pytest.raises(ValueError, match="exceeds"):
            planner.plan_direct_move(invalid_target)

    @given(target=valid_position())
    @settings(max_examples=100)
    def test_accepts_valid_positions(self, target: Position):
        """Planner accepts all valid positions."""
        planner = MotionPlanner(safe_z=50.0)
        commands = planner.plan_direct_move(target)
        assert len(commands) > 0


# =============================================================================
# Pick/Place Sequence Tests
# =============================================================================


class TestPickPlaceSequences:
    """Test pick and place sequence generation."""

    @given(current=valid_position(), pick_pos=valid_position(), safe_z=safe_z_strategy)
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_pick_sequence_invariants(
        self, current: Position, pick_pos: Position, safe_z: float
    ):
        """Pick sequence satisfies motion invariants."""
        planner = MotionPlanner(safe_z=safe_z)
        commands = planner.plan_pick_sequence(current, pick_pos)
        
        # INV-M3: Wait after moves
        passed, msg = verify_wait_after_moves(commands)
        assert passed, f"Pick sequence violates INV-M3: {msg}"

    @given(current=valid_position(), place_pos=valid_position(), safe_z=safe_z_strategy)
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_place_sequence_invariants(
        self, current: Position, place_pos: Position, safe_z: float
    ):
        """Place sequence satisfies motion invariants."""
        planner = MotionPlanner(safe_z=safe_z)
        commands = planner.plan_place_sequence(current, place_pos)
        
        passed, msg = verify_wait_after_moves(commands)
        assert passed, f"Place sequence violates INV-M3: {msg}"


# =============================================================================
# Command Property Tests
# =============================================================================


class TestCommandProperties:
    """Property tests for command types."""

    @given(
        x=st.one_of(st.none(), st.floats(-100, 100, allow_nan=False)),
        y=st.one_of(st.none(), st.floats(100, 300, allow_nan=False)),
        z=st.one_of(st.none(), st.floats(-30, 100, allow_nan=False)),
    )
    def test_move_command_axis_detection(
        self, x: float | None, y: float | None, z: float | None
    ):
        """MoveCommand correctly detects axis changes."""
        assume(x is not None or y is not None or z is not None)
        
        cmd = MoveCommand(x=x, y=y, z=z)
        
        assert cmd.changes_xy() == (x is not None or y is not None)
        assert cmd.changes_z() == (z is not None)
        assert cmd.is_z_only() == (z is not None and x is None and y is None)

    @given(
        x=st.floats(-100, 100, allow_nan=False),
        y=st.floats(100, 300, allow_nan=False),
        z=st.floats(-30, 100, allow_nan=False),
        feedrate=st.sampled_from([1000, 2000, 3000]),
    )
    def test_gcode_format(self, x: float, y: float, z: float, feedrate: int):
        """G-code has correct format."""
        cmd = MoveCommand(x=x, y=y, z=z, feedrate=feedrate)
        gcode = cmd.to_gcode()
        
        assert gcode.startswith("G1 F")
        assert f"F{feedrate}" in gcode
