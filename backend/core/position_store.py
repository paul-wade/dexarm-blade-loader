"""
Position Store - Single responsibility: persist and load positions
"""

import json
from pathlib import Path
from typing import Optional, Protocol
from dataclasses import dataclass, field, asdict
from .types import Position


class IPositionStore(Protocol):
    """Interface for position storage"""
    
    def get_pick(self) -> Optional[Position]: ...
    def set_pick(self, pos: Position) -> None: ...
    def get_hooks(self) -> list[Position]: ...
    def add_hook(self, pos: Position) -> int: ...
    def delete_hook(self, index: int) -> None: ...
    def clear_hooks(self) -> None: ...
    def get_safe_z(self) -> float: ...
    def set_safe_z(self, z: float) -> None: ...


@dataclass
class StoredPositions:
    """Data structure for stored positions"""
    pick: Optional[dict] = None
    safe_z: float = 0
    hooks: list[dict] = field(default_factory=list)


class PositionStore:
    """Persists positions to JSON file"""
    
    def __init__(self, file_path: Optional[Path] = None):
        self.file_path = file_path or Path(__file__).parent.parent / "blade_positions.json"
        self._data = self._load()
    
    def _load(self) -> StoredPositions:
        """Load positions from file"""
        if self.file_path.exists():
            try:
                with open(self.file_path, 'r') as f:
                    data = json.load(f)
                    return StoredPositions(
                        pick=data.get('pick'),
                        safe_z=data.get('safe_z', 0),
                        hooks=data.get('hooks', [])
                    )
            except (json.JSONDecodeError, KeyError):
                pass
        return StoredPositions()
    
    def _save(self) -> None:
        """Save positions to file"""
        data = {
            'pick': self._data.pick,
            'safe_z': self._data.safe_z,
            'hooks': self._data.hooks
        }
        with open(self.file_path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def get_pick(self) -> Optional[Position]:
        """Get pick position"""
        if self._data.pick:
            return Position.from_dict(self._data.pick)
        return None
    
    def set_pick(self, pos: Position) -> None:
        """Set pick position"""
        self._data.pick = pos.to_dict()
        self._save()
    
    def get_hooks(self) -> list[Position]:
        """Get all hook positions"""
        return [Position.from_dict(h) for h in self._data.hooks]
    
    def get_hook(self, index: int) -> Optional[Position]:
        """Get a specific hook position"""
        if 0 <= index < len(self._data.hooks):
            return Position.from_dict(self._data.hooks[index])
        return None
    
    def add_hook(self, pos: Position) -> int:
        """Add a hook position, returns index"""
        self._data.hooks.append(pos.to_dict())
        self._save()
        return len(self._data.hooks) - 1
    
    def update_hook(self, index: int, pos: Position) -> bool:
        """Update a hook position"""
        if 0 <= index < len(self._data.hooks):
            self._data.hooks[index] = pos.to_dict()
            self._save()
            return True
        return False
    
    def delete_hook(self, index: int) -> bool:
        """Delete a hook position"""
        if 0 <= index < len(self._data.hooks):
            del self._data.hooks[index]
            self._save()
            return True
        return False
    
    def clear_hooks(self) -> None:
        """Clear all hooks"""
        self._data.hooks = []
        self._save()
    
    def get_safe_z(self) -> float:
        """Get safe Z height"""
        return self._data.safe_z
    
    def set_safe_z(self, z: float) -> None:
        """Set safe Z height"""
        self._data.safe_z = z
        self._save()
    
    def hook_count(self) -> int:
        """Get number of hooks"""
        return len(self._data.hooks)
    
    def to_dict(self) -> dict:
        """Export all positions as dict (for API)"""
        return {
            'pick': self._data.pick,
            'safe_z': self._data.safe_z,
            'hooks': self._data.hooks
        }
