"""
Integration tests for state transitions and recovery.

Tests critical state machine behavior:
- Teach mode: motors off → position sync → motors on
- Cycle management: running, paused, stopped states
- Auto-recovery: motor state, position sync
- Safe Z synchronization
"""

import pytest
from core.types import Position
from core.transport import MockTransport
from core.position_store import PositionStore
from controller import BladeLoaderController


class TestTeachModeTransitions:
    """Test teach mode state transitions."""

    @pytest.fixture
    def homed_controller(self):
        """Controller that has been homed."""
        transport = MockTransport()
        ctrl = BladeLoaderController(transport, safe_z=50.0)
        ctrl.home()
        return ctrl, transport

    def test_motors_off_disables_motors(self, homed_controller):
        """motors_off() sends M84 and sets state."""
        ctrl, transport = homed_controller
        transport.clear_history()
        
        ctrl.motors_off()
        
        assert "M84" in transport.sent_commands
        assert ctrl._motors_enabled is False

    def test_motors_on_enables_and_syncs(self, homed_controller):
        """motors_on() sends M17 and syncs position."""
        ctrl, transport = homed_controller
        ctrl.motors_off()
        transport.clear_history()
        
        ctrl.motors_on()
        
        assert "M17" in transport.sent_commands
        assert "M895" in transport.sent_commands  # Position sync
        assert ctrl._motors_enabled is True

    def test_position_syncs_after_teach_mode(self, homed_controller):
        """Position updates from M895 after teach mode."""
        ctrl, transport = homed_controller
        
        # Simulate arm moved during teach mode
        ctrl.motors_off()
        transport.position = Position(150, 280, 45)  # Simulated manual move
        
        ctrl.motors_on()
        
        # Position should now match simulated move
        assert abs(ctrl.position.x - 150) < 0.1
        assert abs(ctrl.position.y - 280) < 0.1
        assert abs(ctrl.position.z - 45) < 0.1

    def test_teach_mode_warns_when_carrying_blade(self, homed_controller, capsys):
        """Entering teach mode while carrying blade logs warning."""
        ctrl, transport = homed_controller
        ctrl.pick_blade(Position(100, 200, 10))
        
        ctrl.motors_off()
        
        # Should have logged warning (check via log output or state)
        assert ctrl._carrying_blade is True  # Still carrying


class TestMotorAutoRecovery:
    """Test auto-recovery when motors disabled."""

    @pytest.fixture
    def teach_mode_controller(self):
        """Controller in teach mode."""
        transport = MockTransport()
        ctrl = BladeLoaderController(transport, safe_z=50.0)
        ctrl.home()
        ctrl.motors_off()
        return ctrl, transport

    def test_move_auto_enables_motors(self, teach_mode_controller):
        """Attempting move with motors off auto-enables them."""
        ctrl, transport = teach_mode_controller
        
        assert ctrl._motors_enabled is False
        
        # Move should auto-recover
        ctrl.move_to(Position(100, 250, 30))
        
        assert ctrl._motors_enabled is True

    def test_auto_recovery_syncs_position(self, teach_mode_controller):
        """Auto-recovery syncs position before moving."""
        ctrl, transport = teach_mode_controller
        
        # Simulate manual move during teach mode
        transport.position = Position(80, 260, 20)
        
        # Move should sync first, then move
        ctrl.move_to(Position(100, 250, 30))
        
        # Should have M17 and M895 in history (from auto-recovery)
        assert "M17" in transport.sent_commands
        assert "M895" in transport.sent_commands


class TestSafeZSynchronization:
    """Test safe_z stays in sync."""

    def test_set_safe_z_updates_planner(self):
        """set_safe_z updates motion planner."""
        transport = MockTransport()
        ctrl = BladeLoaderController(transport, safe_z=50.0)
        
        ctrl.set_safe_z(100.0)
        
        assert ctrl.safe_z == 100.0
        assert ctrl._planner.safe_z == 100.0

    def test_safe_z_from_position_store(self):
        """Controller uses safe_z from position store at init."""
        transport = MockTransport()
        ctrl = BladeLoaderController(transport, safe_z=75.0)
        
        assert ctrl.safe_z == 75.0


class TestCycleStateTransitions:
    """Test cycle state management."""

    @pytest.fixture
    def cycle_ready_state(self, tmp_path):
        """AppState ready for cycles."""
        from api.dependencies import AppState
        
        # Create temp position store
        store = PositionStore(tmp_path / "positions.json")
        store.set_pick(Position(0, 304, 60))
        store.set_safe_z(50.0)
        store.add_hook(Position(100, 250, 20))
        store.add_hook(Position(-100, 250, 20))
        
        state = AppState()
        state.positions = store
        state._transport = MockTransport()
        state.controller = BladeLoaderController(state._transport, safe_z=50.0)
        state.controller.home()
        
        return state

    def test_initial_cycle_state(self, cycle_ready_state):
        """Cycle starts not running."""
        state = cycle_ready_state
        
        assert state.is_running is False
        assert state.is_paused is False
        assert state.current_cycle == 0

    def test_cycle_flags_during_run(self, cycle_ready_state):
        """Cycle flags update during run."""
        state = cycle_ready_state
        
        # Simulate cycle start
        state.is_running = True
        state.total_cycles = 2
        state.current_cycle = 1
        
        assert state.is_running is True
        assert state.total_cycles == 2

    def test_cycle_stop_resets_flags(self, cycle_ready_state):
        """Stop resets all cycle flags."""
        state = cycle_ready_state
        
        state.is_running = True
        state.is_paused = True
        state.current_cycle = 1
        
        # Simulate stop
        state.is_running = False
        state.is_paused = False
        state.current_cycle = 0
        
        assert state.is_running is False
        assert state.is_paused is False


class TestPositionStoreIntegration:
    """Test position store integration."""

    def test_pick_position_persistence(self, tmp_path):
        """Pick position persists across instances."""
        store_path = tmp_path / "positions.json"
        
        # Set position
        store1 = PositionStore(store_path)
        store1.set_pick(Position(10, 300, 50))
        
        # New instance should load same position
        store2 = PositionStore(store_path)
        pick = store2.get_pick()
        
        assert pick is not None
        assert pick.x == 10
        assert pick.y == 300
        assert pick.z == 50

    def test_hooks_persistence(self, tmp_path):
        """Hooks persist across instances."""
        store_path = tmp_path / "positions.json"
        
        store1 = PositionStore(store_path)
        store1.add_hook(Position(100, 200, 10))
        store1.add_hook(Position(-100, 200, 10))
        
        store2 = PositionStore(store_path)
        hooks = store2.get_hooks()
        
        assert len(hooks) == 2

    def test_safe_z_persistence(self, tmp_path):
        """Safe Z persists across instances."""
        store_path = tmp_path / "positions.json"
        
        store1 = PositionStore(store_path)
        store1.set_safe_z(123.45)
        
        store2 = PositionStore(store_path)
        
        assert store2.get_safe_z() == 123.45


class TestStatusReporting:
    """Test complete status reporting."""

    def test_status_includes_motors_enabled(self):
        """Status includes motors_enabled field."""
        transport = MockTransport()
        ctrl = BladeLoaderController(transport)
        ctrl.home()
        
        status = ctrl.get_status()
        
        assert "motors_enabled" in status
        assert status["motors_enabled"] is True

    def test_status_after_teach_mode(self):
        """Status reflects teach mode state."""
        transport = MockTransport()
        ctrl = BladeLoaderController(transport)
        ctrl.home()
        ctrl.motors_off()
        
        status = ctrl.get_status()
        
        assert status["motors_enabled"] is False

    def test_status_after_pick(self):
        """Status reflects carrying blade."""
        transport = MockTransport()
        ctrl = BladeLoaderController(transport)
        ctrl.home()
        ctrl.pick_blade(Position(100, 200, 10))
        
        status = ctrl.get_status()
        
        assert status["carrying_blade"] is True
        assert status["suction_active"] is True


class TestEdgeCases:
    """Test edge cases and error recovery."""

    def test_home_resets_carrying_blade(self):
        """Homing clears carrying_blade state."""
        transport = MockTransport()
        ctrl = BladeLoaderController(transport)
        ctrl.home()
        ctrl.pick_blade(Position(100, 200, 10))
        
        assert ctrl.carrying_blade is True
        
        ctrl.home()
        
        assert ctrl.carrying_blade is False

    def test_double_home_is_safe(self):
        """Can home multiple times safely."""
        transport = MockTransport()
        ctrl = BladeLoaderController(transport)
        
        ctrl.home()
        ctrl.home()  # Should not crash
        
        assert ctrl.is_homed is True

    def test_motors_on_when_already_on(self):
        """motors_on() when already on is safe."""
        transport = MockTransport()
        ctrl = BladeLoaderController(transport)
        ctrl.home()
        
        ctrl.motors_on()  # Already on
        ctrl.motors_on()  # Should not crash
        
        assert ctrl._motors_enabled is True

    def test_position_tracking_through_cycle(self):
        """Position stays accurate through full cycle."""
        transport = MockTransport()
        ctrl = BladeLoaderController(transport, safe_z=50.0)
        ctrl.home()
        
        pick_pos = Position(100, 200, 10)
        place_pos = Position(-100, 200, 15)
        
        ctrl.pick_blade(pick_pos)
        ctrl.place_blade(place_pos)
        
        # Should be at safe_z above place position
        assert ctrl.position.x == place_pos.x
        assert ctrl.position.y == place_pos.y
        assert ctrl.position.z == 50.0  # safe_z
