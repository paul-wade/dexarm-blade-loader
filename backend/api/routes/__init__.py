"""API Routes - Domain-based routing"""

from .connection import router as connection_router
from .movement import router as movement_router
from .positions import router as positions_router
from .suction import router as suction_router
from .cycles import router as cycles_router

__all__ = [
    'connection_router',
    'movement_router',
    'positions_router',
    'suction_router',
    'cycles_router',
]
