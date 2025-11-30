"""
API Endpoint Tests

Tests the FastAPI endpoints using TestClient with MockTransport.
"""

import pytest
from fastapi.testclient import TestClient

from api.app import create_app
from api.dependencies import get_app_state, _app_state


@pytest.fixture
def client():
    """Create test client with fresh app state."""
    global _app_state
    
    # Reset app state
    import api.dependencies
    api.dependencies._app_state = None
    
    app = create_app()
    with TestClient(app) as client:
        yield client
    
    # Cleanup
    api.dependencies._app_state = None


@pytest.fixture
def connected_client(client):
    """Client connected to mock transport."""
    response = client.post("/api/connect", json={"port": "mock"})
    assert response.json()["success"]
    return client


@pytest.fixture
def homed_client(connected_client):
    """Client connected and homed."""
    response = connected_client.post("/api/home")
    assert response.json()["success"]
    return connected_client


class TestConnectionEndpoints:
    """Test connection endpoints."""

    def test_get_status_disconnected(self, client):
        """Status shows disconnected initially."""
        response = client.get("/api/status")
        assert response.status_code == 200
        data = response.json()
        assert data["connected"] is False

    def test_connect_mock(self, client):
        """Can connect to mock transport."""
        response = client.post("/api/connect", json={"port": "mock"})
        assert response.status_code == 200
        assert response.json()["success"]

    def test_status_after_connect(self, connected_client):
        """Status shows connected after connect."""
        response = connected_client.get("/api/status")
        data = response.json()
        assert data["connected"] is True
        assert data["homed"] is False

    def test_disconnect(self, connected_client):
        """Can disconnect."""
        response = connected_client.post("/api/disconnect")
        assert response.json()["success"]
        
        # Verify disconnected
        response = connected_client.get("/api/status")
        assert response.json()["connected"] is False

    def test_history_empty(self, connected_client):
        """History is empty initially."""
        response = connected_client.get("/api/history")
        assert response.status_code == 200
        assert response.json()["history"] == []


class TestMovementEndpoints:
    """Test movement endpoints."""

    def test_home(self, connected_client):
        """Home sets position to 0,300,0."""
        response = connected_client.post("/api/home")
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"]
        assert data["position"]["x"] == 0
        assert data["position"]["y"] == 300
        assert data["position"]["z"] == 0

    def test_status_after_home(self, homed_client):
        """Status shows homed after home."""
        response = homed_client.get("/api/status")
        data = response.json()
        assert data["homed"] is True

    def test_move_requires_home(self, connected_client):
        """Move fails if not homed."""
        response = connected_client.post("/api/move", json={"x": 100, "y": 200, "z": 50})
        assert response.status_code == 400

    def test_move_to_position(self, homed_client):
        """Can move to position after home."""
        response = homed_client.post("/api/move", json={"x": 100, "y": 200, "z": 50})
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"]
        assert data["position"]["x"] == 100
        assert data["position"]["y"] == 200
        assert data["position"]["z"] == 50

    def test_safe_move(self, homed_client):
        """Safe move works."""
        response = homed_client.post("/api/safe_move", json={"x": 100, "y": 200, "z": 10})
        assert response.status_code == 200
        assert response.json()["success"]

    def test_jog_z(self, homed_client):
        """Jog Z axis."""
        response = homed_client.post("/api/jog", json={"axis": "z", "distance": 20})
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"]
        assert data["position"]["z"] == 20  # 0 + 20

    def test_jog_invalid_axis(self, homed_client):
        """Jog with invalid axis fails."""
        response = homed_client.post("/api/jog", json={"axis": "w", "distance": 10})
        assert response.status_code == 400

    def test_get_position(self, homed_client):
        """Get position returns tracked position."""
        response = homed_client.get("/api/position")
        assert response.status_code == 200
        assert response.json()["position"]["y"] == 300

    def test_teach_mode(self, homed_client):
        """Enable/disable teach mode."""
        response = homed_client.post("/api/teach/enable")
        assert response.json()["success"]
        
        response = homed_client.post("/api/teach/disable")
        assert response.json()["success"]

    def test_estop(self, homed_client):
        """Emergency stop."""
        response = homed_client.post("/api/estop")
        assert response.status_code == 200
        assert response.json()["success"]


class TestCycleEndpoints:
    """Test pick/place cycle endpoints."""

    def test_pick_blade(self, homed_client):
        """Pick blade at position."""
        response = homed_client.post("/api/cycle/pick", json={"x": 100, "y": 200, "z": 10})
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"]
        assert data["carrying_blade"] is True

    def test_place_blade(self, homed_client):
        """Place blade after picking."""
        # Pick first
        homed_client.post("/api/cycle/pick", json={"x": 100, "y": 200, "z": 10})
        
        # Then place
        response = homed_client.post("/api/cycle/place", json={"x": -100, "y": 200, "z": 10})
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"]
        assert data["carrying_blade"] is False

    def test_place_without_pick_fails(self, homed_client):
        """Cannot place without picking first."""
        response = homed_client.post("/api/cycle/place", json={"x": -100, "y": 200, "z": 10})
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert "carrying" in data["message"].lower()

    def test_cycle_state(self, homed_client):
        """Get cycle state."""
        response = homed_client.get("/api/cycle/state")
        assert response.status_code == 200
        
        data = response.json()
        assert "is_running" in data
        assert data["is_running"] is False


class TestSuctionEndpoints:
    """Test suction control endpoints."""

    def test_suction_on(self, connected_client):
        """Turn suction on."""
        # Need to home first for controller
        connected_client.post("/api/home")
        
        response = connected_client.post("/api/suction/on")
        assert response.status_code == 200
        assert response.json()["success"]

    def test_suction_off(self, connected_client):
        """Turn suction off."""
        connected_client.post("/api/home")
        
        response = connected_client.post("/api/suction/off")
        assert response.status_code == 200
        assert response.json()["success"]

    def test_suction_blow(self, connected_client):
        """Blow air."""
        connected_client.post("/api/home")
        
        response = connected_client.post("/api/suction/blow")
        assert response.status_code == 200
        assert response.json()["success"]

    def test_suction_release(self, connected_client):
        """Release pressure."""
        connected_client.post("/api/home")
        
        response = connected_client.post("/api/suction/release")
        assert response.status_code == 200
        assert response.json()["success"]


class TestHistoryEndpoint:
    """Test command history."""

    def test_history_records_commands(self, homed_client):
        """Commands are recorded in history."""
        # Do some operations
        homed_client.post("/api/move", json={"x": 100, "y": 200, "z": 50})
        
        response = homed_client.get("/api/history")
        history = response.json()["history"]
        
        assert len(history) > 0
        # Check history entry format
        entry = history[0]
        assert "gcode" in entry
        assert "timestamp" in entry
        assert "success" in entry

    def test_history_limit(self, homed_client):
        """History respects limit parameter."""
        # Generate some commands
        for _ in range(5):
            homed_client.post("/api/jog", json={"axis": "z", "distance": 1})
        
        response = homed_client.get("/api/history?limit=3")
        history = response.json()["history"]
        
        assert len(history) <= 3
