from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
from backend.app.core.config import get_settings

settings = get_settings()

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
)

# -------------------------------------------------------------------
# CORS
# -------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------------------------------------------------
# Routers
# -------------------------------------------------------------------
from backend.app.api.routes import upload          # noqa: E402
app.include_router(upload.router, prefix="/upload", tags=["Upload"])

from backend.app.api.routes import analysis       # noqa: E402
from backend.app.api.routes import report          # noqa: E402
app.include_router(analysis.router, prefix="/analysis", tags=["Analysis"])
app.include_router(report.router,   prefix="/report",   tags=["Report"])

from backend.app.api.routes import chat           # noqa: E402
app.include_router(chat.router,     prefix="/chat",     tags=["Chat"])


# -------------------------------------------------------------------
# Health check
# -------------------------------------------------------------------
@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok", "version": settings.VERSION}


# -------------------------------------------------------------------
# Serve React frontend (production build)
# -------------------------------------------------------------------
STATIC_DIR = Path("/app/static")

if STATIC_DIR.exists():
    # Serve built assets (JS, CSS, images)
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")

    # SPA fallback — serve index.html for all non-API routes
    @app.get("/{full_path:path}")
    async def serve_spa(request: Request, full_path: str):
        # Don't intercept API routes or docs
        if full_path.startswith(("upload", "analysis", "report", "chat", "health", "docs", "redoc", "openapi")):
            return
        file_path = STATIC_DIR / full_path
        if file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(STATIC_DIR / "index.html")