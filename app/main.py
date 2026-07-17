"""
Main FastAPI application entry point — Phase 2.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import tickets
from app.routers import profiles
from app.services.dataset import init_dataset
from app.services.profile_registry import init_profiles

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load dataset and profiles once at startup."""
    settings = get_settings()
    logger.info("Loading dataset from %s …", settings.dataset_path)
    init_dataset(settings.dataset_path)
    logger.info("Loading company profiles …")
    init_profiles("profiles")
    logger.info("Startup complete.")
    yield
    logger.info("Shutting down.")


app = FastAPI(
    title="Agentic Triage Framework",
    description=(
        "Phase 2 — Agentic AI framework for risk-aware task triage with "
        "configurable company profiles. Same ticket, different profile → "
        "different autonomy decision."
    ),
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(tickets.router,  prefix="/tickets",  tags=["Tickets"])
app.include_router(profiles.router, prefix="/profiles", tags=["Profiles"])


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "ok", "phase": "2"}
