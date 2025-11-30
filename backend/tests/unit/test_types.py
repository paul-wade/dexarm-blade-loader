"""
Unit tests for core types.
Task 1.1: Immutable Data Types
"""

import math
import pytest
from core.types import (
    Position,
    WorkspaceLimits,
    MoveCommand,
    WaitCommand,
    HomeCommand,
    SuctionCommand,
    DEFAULT_WORKSPACE,
)


class TestPosition:
    """Tests for Position dataclass."""

    def test_immutable(self):
        """Position is immutable (frozen)."""
        pos = Position(x=100, y=200, z=50)
        with pytest.raises(AttributeError):
            pos.x = 150  # type: ignore

    def test_distance_to(self):
        """Euclidean distance calculation."""
        p1 = Position(0, 0, 0)
        p2 = Position(3, 4, 0)
        assert p1.distance_to(p2) == 5.0

    def test_xy_distance(self):
        """XY plane distance ignores Z."""
        p1 = Position(0, 0, 0)
        p2 = Position(3, 4, 100)  # Z is different but ignored
        assert p1.xy_distance_to(p2) == 5.0

    def test_reach(self):
        """Reach is distance from origin in XY plane."""
        pos = Position(x=3, y=4, z=50)
        assert pos.reach() == 5.0

    def test_with_z(self):
        """with_z creates new position with different Z."""
        pos = Position(100, 200, 50)
        new_pos = pos.with_z(100)
        
        assert new_pos.x == 100
        assert new_pos.y == 200
        assert new_pos.z == 100
        assert pos.z == 50  # Original unchanged

    def test_to_dict_round_trip(self):
        """Position can be serialized to dict and back."""
        pos = Position(100.5, 200.25, 50.75)
        d = pos.to_dict()
        restored = Position.from_dict(d)
        
        assert restored == pos

    def test_hashable(self):
        """Position can be used as dict key."""
        pos = Position(100, 200, 50)
        d = {pos: "test"}
        assert d[Position(100, 200, 50)] == "test"


class TestWorkspaceLimits:
    """Tests for workspace validation."""

    def test_valid_position(self):
        """Accept position within all limits."""
        pos = Position(x=0, y=250, z=50)
        valid, msg = DEFAULT_WORKSPACE.validate(pos)
        assert valid
        assert msg == "OK"

    def test_x_too_low(self):
        """Reject X below minimum."""
        pos = Position(x=-350, y=250, z=50)  # Below x_min=-300
        valid, msg = DEFAULT_WORKSPACE.validate(pos)
        assert not valid
        assert "X=" in msg

    def test_x_too_high(self):
        """Reject X above maximum."""
        pos = Position(x=350, y=250, z=50)  # Above x_max=300
        valid, msg = DEFAULT_WORKSPACE.validate(pos)
        assert not valid
        assert "X=" in msg

    def test_y_too_low(self):
        """Reject Y below minimum (behind arm base)."""
        pos = Position(x=0, y=50, z=50)
        valid, msg = DEFAULT_WORKSPACE.validate(pos)
        assert not valid
        assert "Y=" in msg

    def test_z_too_low(self):
        """Reject Z below minimum."""
        pos = Position(x=0, y=250, z=-150)  # Below z_min=-100
        valid, msg = DEFAULT_WORKSPACE.validate(pos)
        assert not valid
        assert "Z=" in msg

    def test_reach_exceeded(self):
        """Reject position beyond arm reach."""
        # X=300, Y=350 gives reach of ~460mm, exceeds 400mm limit
        pos = Position(x=300, y=350, z=50)
        valid, msg = DEFAULT_WORKSPACE.validate(pos)
        assert not valid
        assert "Reach" in msg


class TestMoveCommand:
    """Tests for MoveCommand."""

    def test_full_xyz_gcode(self):
        """Full XYZ move generates correct G-code."""
        cmd = MoveCommand(x=100.5, y=200.25, z=50.0, feedrate=3000)
        assert cmd.to_gcode() == "G1 F3000 X100.50 Y200.25 Z50.00"

    def test_z_only_gcode(self):
        """Z-only move generates correct G-code."""
        cmd = MoveCommand(z=75.0, feedrate=2000)
        assert cmd.to_gcode() == "G1 F2000 Z75.00"

    def test_xy_only_gcode(self):
        """XY-only move generates correct G-code."""
        cmd = MoveCommand(x=100.0, y=200.0, feedrate=3000)
        assert cmd.to_gcode() == "G1 F3000 X100.00 Y200.00"

    def test_requires_at_least_one_axis(self):
        """MoveCommand requires at least one axis."""
        with pytest.raises(ValueError):
            MoveCommand(feedrate=3000)

    def test_changes_xy(self):
        """changes_xy detects X or Y changes."""
        assert MoveCommand(x=100, feedrate=3000).changes_xy()
        assert MoveCommand(y=200, feedrate=3000).changes_xy()
        assert MoveCommand(x=100, y=200, feedrate=3000).changes_xy()
        assert not MoveCommand(z=50, feedrate=3000).changes_xy()

    def test_changes_z(self):
        """changes_z detects Z changes."""
        assert MoveCommand(z=50, feedrate=3000).changes_z()
        assert not MoveCommand(x=100, feedrate=3000).changes_z()

    def test_is_z_only(self):
        """is_z_only detects Z-only moves."""
        assert MoveCommand(z=50, feedrate=3000).is_z_only()
        assert not MoveCommand(x=100, z=50, feedrate=3000).is_z_only()

    def test_is_xy_only(self):
        """is_xy_only detects XY-only moves."""
        assert MoveCommand(x=100, feedrate=3000).is_xy_only()
        assert MoveCommand(x=100, y=200, feedrate=3000).is_xy_only()
        assert not MoveCommand(z=50, feedrate=3000).is_xy_only()


class TestOtherCommands:
    """Tests for other command types."""

    def test_wait_command(self):
        """WaitCommand generates M400."""
        assert WaitCommand().to_gcode() == "M400"

    def test_home_command(self):
        """HomeCommand generates M1112."""
        assert HomeCommand().to_gcode() == "M1112"

    def test_suction_on(self):
        """Suction ON generates M1000."""
        assert SuctionCommand("on").to_gcode() == "M1000"

    def test_suction_release(self):
        """Suction release generates M1002."""
        assert SuctionCommand("release").to_gcode() == "M1002"

    def test_suction_off(self):
        """Suction OFF generates M1003."""
        assert SuctionCommand("off").to_gcode() == "M1003"

    def test_suction_blow(self):
        """Suction blow generates M1001."""
        assert SuctionCommand("blow").to_gcode() == "M1001"
