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
# Routers  (uncomment each as the phase is implemented)
# -------------------------------------------------------------------
# from app.api.routes import upload, analysis, report, chat
# app.include_router(upload.router,   prefix="/upload",            tags=["Upload"])
# app.include_router(analysis.router, prefix="/analysis",          tags=["Analysis"])
# app.include_router(report.router,   prefix="/report",            tags=["Report"])
# app.include_router(chat.router,     prefix="/chat",              tags=["Chat"])


# -------------------------------------------------------------------
# Health check
# -------------------------------------------------------------------
@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok", "version": settings.VERSION}