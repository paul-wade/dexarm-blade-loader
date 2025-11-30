"""
Unit tests for command execution layer.

Task 2.1: Command Queue
Task 2.2: Transport Abstraction
"""

import pytest
from datetime import datetime

from core.types import MoveCommand, WaitCommand, HomeCommand, SuctionCommand, Position
from core.executor import CommandQueue, CommandResult
from core.transport import MockTransport, Transport


class TestCommandQueue:
    """Tests for CommandQueue."""

    def test_enqueue_commands(self):
        """Commands can be enqueued."""
        queue = CommandQueue()
        queue.enqueue(HomeCommand())
        queue.enqueue(MoveCommand(z=50, feedrate=3000))
        
        assert queue.pending_count() == 2

    def test_execute_all_sends_commands(self):
        """execute_all sends all commands via transport."""
        transport = MockTransport()
        queue = CommandQueue()
        
        queue.enqueue(HomeCommand())
        queue.enqueue(MoveCommand(x=100, y=200, z=50, feedrate=3000))
        queue.enqueue(WaitCommand())
        
        queue.execute_all(transport)
        
        assert transport.command_count == 3
        assert "M1112" in transport.sent_commands
        assert any("G1" in cmd for cmd in transport.sent_commands)
        assert "M400" in transport.sent_commands

    def test_execute_all_clears_queue(self):
        """Queue is empty after execute_all."""
        transport = MockTransport()
        queue = CommandQueue()
        
        queue.enqueue(HomeCommand())
        queue.execute_all(transport)
        
        assert queue.pending_count() == 0

    def test_history_records_all_commands(self):
        """History records all executed commands."""
        transport = MockTransport()
        queue = CommandQueue()
        
        queue.enqueue(HomeCommand())
        queue.enqueue(WaitCommand())
        queue.execute_all(transport)
        
        history = queue.get_history()
        assert len(history) == 2
        assert all(isinstance(r, CommandResult) for r in history)

    def test_history_includes_timestamp(self):
        """Each history entry has a timestamp."""
        transport = MockTransport()
        queue = CommandQueue()
        
        queue.enqueue(HomeCommand())
        queue.execute_all(transport)
        
        history = queue.get_history()
        assert history[0].timestamp is not None
        assert isinstance(history[0].timestamp, datetime)

    def test_history_includes_gcode(self):
        """Each history entry includes the G-code sent."""
        transport = MockTransport()
        queue = CommandQueue()
        
        queue.enqueue(HomeCommand())
        queue.execute_all(transport)
        
        history = queue.get_history()
        assert history[0].gcode == "M1112"

    def test_clear_clears_pending(self):
        """clear() removes pending commands."""
        queue = CommandQueue()
        queue.enqueue(HomeCommand())
        queue.enqueue(WaitCommand())
        
        queue.clear()
        
        assert queue.pending_count() == 0

    def test_clear_preserves_history(self):
        """clear() preserves execution history."""
        transport = MockTransport()
        queue = CommandQueue()
        
        queue.enqueue(HomeCommand())
        queue.execute_all(transport)
        
        queue.enqueue(WaitCommand())
        queue.clear()
        
        assert len(queue.get_history()) == 1


class TestMockTransport:
    """Tests for MockTransport."""

    def test_send_returns_ok(self):
        """send() returns 'ok' response."""
        transport = MockTransport()
        response = transport.send("M1112")
        assert response == "ok"

    def test_tracks_sent_commands(self):
        """Tracks all sent commands."""
        transport = MockTransport()
        transport.send("M1112")
        transport.send("G1 F3000 X100 Y200 Z50")
        
        assert len(transport.sent_commands) == 2
        assert "M1112" in transport.sent_commands

    def test_simulates_home_position(self):
        """M1112 sets position to home."""
        transport = MockTransport()
        transport.send("M1112")
        
        assert transport.position == Position(0, 300, 0)

    def test_simulates_move(self):
        """G1 updates simulated position."""
        transport = MockTransport()
        transport.send("M1112")
        transport.send("G1 F3000 X100 Y200 Z50")
        
        assert transport.position.x == 100
        assert transport.position.y == 200
        assert transport.position.z == 50

    def test_partial_move_updates_only_specified(self):
        """G1 with partial axes only updates those axes."""
        transport = MockTransport()
        transport.send("M1112")  # Position: 0, 300, 0
        transport.send("G1 F3000 Z50")  # Only Z
        
        assert transport.position.x == 0
        assert transport.position.y == 300
        assert transport.position.z == 50

    def test_is_connected(self):
        """MockTransport is always connected."""
        transport = MockTransport()
        assert transport.is_connected

    def test_m114_returns_position(self):
        """M114 returns current position string."""
        transport = MockTransport()
        transport.send("M1112")
        response = transport.send("M114")
        
        assert "X:0" in response
        assert "Y:300" in response
        assert "Z:0" in response


class TestTransportProtocol:
    """Verify MockTransport satisfies Transport protocol."""

    def test_has_send(self):
        """Transport has send method."""
        transport = MockTransport()
        assert hasattr(transport, "send")
        assert callable(transport.send)

    def test_has_is_connected(self):
        """Transport has is_connected property."""
        transport = MockTransport()
        assert hasattr(transport, "is_connected")
        assert isinstance(transport.is_connected, bool)
