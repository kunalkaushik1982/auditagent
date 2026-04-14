"""
Main FastAPI application entry point.
File: backend/app/main.py

This module initializes the FastAPI application, configures middleware,
and registers all API routes.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from backend.app.core.config import settings
from backend.app.api import auth, audits, notifications

# Initialize FastAPI app
app = FastAPI(
    title="Delivery Audit Agent",
    description="AI-powered multi-agent system for automating quality audits",
    version="1.0.0"
)

# Configure CORS - Allow all origins for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(audits.router, prefix="/api/audits", tags=["Audits"])
app.include_router(notifications.router, prefix="/api/notifications", tags=["Notifications"])
# TODO: Include other routers
# app.include_router(agents.router, prefix="/api/agents", tags=["Agents"])

@app.get("/")
async def root():
    """Root endpoint - health check"""
    return {
        "status": "online",
        "service": "Delivery Audit Agent API",
        "version": "1.0.0"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    # TODO: Add database and Redis connectivity checks
    return {"status": "healthy"}

# TODO: Add startup and shutdown event handlers
# @app.on_event("startup")
# async def startup_event():
#     """Initialize database and other resources"""
#     pass

# @app.on_event("shutdown")
# async def shutdown_event():
#     """Clean up resources"""
#     pass
