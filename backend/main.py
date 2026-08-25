"""
main.py — FastAPI application entry point for Scan-X.
Serves both the API and the built React frontend.
"""

import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from backend.database import init_db
from backend.api import targets, crawls, endpoints, reports, github_api, assessments

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("scanx")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIST = os.path.join(BASE_DIR, "frontend", "dist")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Scan-X starting - initializing database...")
    init_db()
    logger.info("Database ready.")
    if os.path.exists(FRONTEND_DIST):
        logger.info(f"Serving frontend from {FRONTEND_DIST}")
    else:
        logger.warning(f"Frontend build not found at {FRONTEND_DIST} — run 'npm run build' in frontend/")
    yield
    logger.info("Scan-X shutting down.")


app = FastAPI(
    title="Scan-X Endpoint Discovery Platform",
    description="Web crawler and endpoint discovery platform for penetration testers.",
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── API Routes ──────────────────────────────────────────────────────────────
app.include_router(targets.router)
app.include_router(crawls.router)
app.include_router(endpoints.router)
app.include_router(reports.router)
app.include_router(github_api.router)
app.include_router(assessments.router)


@app.get("/api/health", tags=["Health"])
def health():
    return {"status": "healthy"}


# ── Serve Built Frontend ───────────────────────────────────────────────────
if os.path.exists(FRONTEND_DIST):
    app.mount("/assets", StaticFiles(directory=os.path.join(FRONTEND_DIST, "assets")), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(request: Request, full_path: str):
        """Serve the React SPA — all non-API routes return index.html."""
        file_path = os.path.join(FRONTEND_DIST, full_path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(FRONTEND_DIST, "index.html"))
