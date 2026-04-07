import os

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.logging_conf import setup_logging
from api.middleware.auth import APIKeyMiddleware
from api.routers import github as github_router
from api.routers import projects as projects_router

# Initialize structured logging
setup_logging()
logger = structlog.get_logger()

app = FastAPI(
    title="AutoForge API",
    description="Multi-agent software development system",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(
    APIKeyMiddleware,
    environment=os.environ.get("ENVIRONMENT", "development"),
)

app.include_router(projects_router.router)
app.include_router(github_router.router)


@app.on_event("startup")
async def startup_event():
    logger.info("api_startup", version="0.1.0", phase=0)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "phase": "0"}


@app.get("/api/status")
async def status() -> dict:
    return {
        "pipeline": "not_built",
        "phase": 0,
        "message": "Execution pipeline not yet built",
    }
