"""
Integration tests for BladeLoaderController.

Task 4.2: Integration Tests

Tests full pick-place cycles with MockTransport to verify
all components work together correctly.
"""

import pytest
from core.types import Position
from core.transport import MockTransport
from controller import BladeLoaderController


class TestControllerInitialization:
    """Test controller setup."""

    def test_creates_with_mock_transport(self):
        """Can create controller with mock transport."""
        transport = MockTransport()
        ctrl = BladeLoaderController(transport)
        assert ctrl is not None

    def test_initial_position_is_unknown(self):
        """Position is unknown until homed."""
        transport = MockTransport()
        ctrl = BladeLoaderController(transport)
        assert not ctrl.is_homed

    def test_home_sets_known_position(self):
        """Homing establishes known position."""
        transport = MockTransport()
        ctrl = BladeLoaderController(transport)
        
        ctrl.home()
        
        assert ctrl.is_homed
        assert ctrl.position == Position(0, 300, 0)


class TestControllerMovement:
    """Test movement operations."""

    @pytest.fixture
    def homed_controller(self):
        """Controller that has been homed."""
        transport = MockTransport()
        ctrl = BladeLoaderController(transport)
        ctrl.home()
        return ctrl, transport

    def test_move_to_updates_position(self, homed_controller):
        """move_to updates tracked position."""
        ctrl, transport = homed_controller
        
        target = Position(100, 250, 50)
        ctrl.move_to(target)
        
        assert ctrl.position == target

    def test_move_to_sends_gcode(self, homed_controller):
        """move_to sends G-code commands."""
        ctrl, transport = homed_controller
        transport.clear_history()
        
        ctrl.move_to(Position(100, 250, 50))
        
        assert any("G1" in cmd for cmd in transport.sent_commands)

    def test_safe_move_lifts_first(self, homed_controller):
        """safe_move_to lifts Z before XY."""
        ctrl, transport = homed_controller
        
        # Move to low position first
        ctrl.move_to(Position(0, 300, 10))
        transport.clear_history()
        
        # Safe move to different XY
        ctrl.safe_move_to(Position(100, 250, 10))
        
        # Should have lifted first
        commands = transport.sent_commands
        z_moves = [c for c in commands if "Z" in c and "X" not in c and "Y" not in c]
        xy_moves = [c for c in commands if "X" in c or "Y" in c]
        
        if z_moves and xy_moves:
            first_z_idx = commands.index(z_moves[0])
            first_xy_idx = commands.index(xy_moves[0])
            assert first_z_idx < first_xy_idx

    def test_rejects_move_before_home(self):
        """Cannot move before homing."""
        transport = MockTransport()
        ctrl = BladeLoaderController(transport)
        
        with pytest.raises(RuntimeError, match="[Hh]ome"):
            ctrl.move_to(Position(100, 250, 50))


class TestControllerPickPlace:
    """Test pick and place operations."""

    @pytest.fixture
    def ready_controller(self):
        """Controller ready for pick/place."""
        transport = MockTransport()
        ctrl = BladeLoaderController(transport)
        ctrl.home()
        return ctrl, transport

    def test_pick_blade_activates_suction(self, ready_controller):
        """pick_blade turns on suction."""
        ctrl, transport = ready_controller
        
        ctrl.pick_blade(Position(100, 200, 10))
        
        assert "M1000" in transport.sent_commands

    def test_pick_blade_updates_carrying_state(self, ready_controller):
        """pick_blade sets carrying_blade flag."""
        ctrl, transport = ready_controller
        
        ctrl.pick_blade(Position(100, 200, 10))
        
        assert ctrl.carrying_blade

    def test_place_blade_releases_suction(self, ready_controller):
        """place_blade releases suction."""
        ctrl, transport = ready_controller
        
        ctrl.pick_blade(Position(100, 200, 10))
        transport.clear_history()
        
        ctrl.place_blade(Position(-100, 200, 10))
        
        # Should have M1002 (release) or M1003 (off)
        assert any(cmd in transport.sent_commands for cmd in ["M1002", "M1003"])

    def test_place_blade_clears_carrying_state(self, ready_controller):
        """place_blade clears carrying_blade flag."""
        ctrl, transport = ready_controller
        
        ctrl.pick_blade(Position(100, 200, 10))
        ctrl.place_blade(Position(-100, 200, 10))
        
        assert not ctrl.carrying_blade

    def test_cannot_place_without_pick(self, ready_controller):
        """Cannot place if not carrying blade."""
        ctrl, transport = ready_controller
        
        with pytest.raises(RuntimeError, match="[Cc]arrying"):
            ctrl.place_blade(Position(-100, 200, 10))


class TestFullCycle:
    """Test complete pick-place cycles."""

    def test_full_pick_place_cycle(self):
        """Complete pick-place cycle works."""
        transport = MockTransport()
        ctrl = BladeLoaderController(transport)
        
        pick_pos = Position(100, 200, 10)
        place_pos = Position(-100, 200, 10)
        
        ctrl.home()
        ctrl.pick_blade(pick_pos)
        ctrl.place_blade(place_pos)
        
        # Should end at safe_z above place position
        assert ctrl.position.z == ctrl.safe_z
        assert not ctrl.carrying_blade

    def test_multiple_cycles(self):
        """Can run multiple pick-place cycles."""
        transport = MockTransport()
        ctrl = BladeLoaderController(transport)
        ctrl.home()
        
        for i in range(3):
            ctrl.pick_blade(Position(100, 200, 10))
            ctrl.place_blade(Position(-100, 200, 10))
        
        assert not ctrl.carrying_blade

    def test_position_tracking_accurate(self):
        """Position stays in sync with mock transport."""
        transport = MockTransport()
        ctrl = BladeLoaderController(transport)
        
        ctrl.home()
        ctrl.pick_blade(Position(100, 200, 10))
        ctrl.place_blade(Position(-100, 200, 10))
        
        # Controller position should match transport simulation
        assert abs(ctrl.position.x - transport.position.x) < 0.1
        assert abs(ctrl.position.y - transport.position.y) < 0.1
        assert abs(ctrl.position.z - transport.position.z) < 0.1

    def test_command_history_complete(self):
        """All commands recorded in history."""
        transport = MockTransport()
        ctrl = BladeLoaderController(transport)
        
        ctrl.home()
        ctrl.pick_blade(Position(100, 200, 10))
        ctrl.place_blade(Position(-100, 200, 10))
        
        history = ctrl.get_command_history()
        assert len(history) > 0
        
        # Check key commands present
        gcodes = [r.gcode for r in history]
        assert "M1112" in gcodes  # Home
        assert "M1000" in gcodes  # Suction on


class TestControllerStatus:
    """Test status reporting."""

    def test_get_status(self):
        """get_status returns current state."""
        transport = MockTransport()
        ctrl = BladeLoaderController(transport)
        ctrl.home()
        
        status = ctrl.get_status()
        
        assert "position" in status
        assert "homed" in status
        assert "carrying_blade" in status
        assert status["homed"] is True
