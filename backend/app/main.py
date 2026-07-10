from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import get_settings

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
from app.api.routes import upload          # noqa: E402
app.include_router(upload.router, prefix="/upload", tags=["Upload"])

from app.api.routes import analysis       # noqa: E402
from app.api.routes import report          # noqa: E402
app.include_router(analysis.router, prefix="/analysis", tags=["Analysis"])
app.include_router(report.router,   prefix="/report",   tags=["Report"])

# Uncomment when Phase 10 is completed:
# from app.api.routes import chat
# app.include_router(chat.router,     prefix="/chat",     tags=["Chat"])


# -------------------------------------------------------------------
# Health check
# -------------------------------------------------------------------
@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok", "version": settings.VERSION}