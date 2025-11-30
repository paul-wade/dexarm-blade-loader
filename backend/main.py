"""
DexArm Blade Loader - Main Entry Point
Production-ready with SOLID architecture and safety interlocks

Run with: uvicorn main:app --reload --port 8000
"""

import sys
import os
from pathlib import Path

# Add backend to path for imports
backend_path = Path(__file__).parent
sys.path.insert(0, str(backend_path))

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# Import the new modular API
from api.app import create_app
from api.dependencies import get_services


def create_full_app() -> FastAPI:
    """Create the full application with static file serving"""
    
    # Create API app
    app = create_app()
    
    # Mount frontend (if exists)
    frontend_path = backend_path.parent / "frontend" / "build"
    if frontend_path.exists():
        app.mount("/", StaticFiles(directory=str(frontend_path), html=True), name="frontend")
    
    return app


# Create app instance
app = create_full_app()


# === Startup/Shutdown Events ===

@app.on_event("startup")
async def startup_event():
    """Initialize on startup"""
    print("=" * 50)
    print("  DexArm Blade Loader v2.0")
    print("  Production-Ready with Safety Interlocks")
    print("=" * 50)
    print()
    print("Safety Features:")
    print("  ✓ XY Interlock: Must be at safe Z for XY movement")
    print("  ✓ Position Verification: Confirms moves completed")
    print("  ✓ Retry Logic: Auto-retry on verification failure")
    print("  ✓ State Machine: Reliable workflow orchestration")
    print()
    
    # Load saved positions
    services = get_services()
    safe_z = services.positions.get_safe_z()
    hooks = services.positions.hook_count()
    pick = services.positions.get_pick()
    
    print("Loaded Positions:")
    print(f"  Safe Z: {safe_z:.1f}mm" if safe_z > 0 else "  Safe Z: Not set")
    print(f"  Pick: ({pick.x:.1f}, {pick.y:.1f}, {pick.z:.1f})" if pick else "  Pick: Not set")
    print(f"  Hooks: {hooks}")
    print()
    print("API ready at http://localhost:8000")
    print("Docs at http://localhost:8000/docs")
    print()


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    services = get_services()
    try:
        if services.is_connected and services.suction:
            print("[SHUTDOWN] Disconnecting from arm...")
            services.suction.off()
            services.disconnect()
    except Exception as e:
        print(f"[SHUTDOWN] Error during cleanup: {e}")


# === Health Check ===

@app.get("/health")
def health_check():
    """Health check endpoint"""
    services = get_services()
    return {
        "status": "ok",
        "version": "2.0.0",
        "connected": services.is_connected,
        "safety": {
            "xy_interlock": services.arm.settings.require_safe_z_for_xy if services.arm else True,
            "position_verification": services.arm.settings.verify_moves if services.arm else True,
            "safe_z": services.arm.settings.safe_z if services.arm else 0,
        }
    }


# === Run directly ===

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
