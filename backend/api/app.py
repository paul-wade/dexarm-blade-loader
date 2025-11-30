"""
FastAPI App Factory - Creates and configures the app
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .routes import (
    connection_router,
    movement_router,
    positions_router,
    suction_router,
    cycles_router,
)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application"""
    
    app = FastAPI(
        title="DexArm Blade Loader API",
        description="REST API for DexArm pick-and-place blade loader",
        version="2.0.0",
    )
    
    # CORS - must be added first
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Global exception handler to ensure CORS headers on errors
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        return JSONResponse(
            status_code=500,
            content={"detail": str(exc)},
        )
    
    # Register routers with /api prefix
    app.include_router(connection_router, prefix="/api")
    app.include_router(movement_router, prefix="/api")
    app.include_router(positions_router, prefix="/api")
    app.include_router(suction_router, prefix="/api")
    app.include_router(cycles_router, prefix="/api")
    
    return app
