import os
from uuid import UUID
from pathlib import Path

from backend.app.core.config import get_settings

settings = get_settings()

# Allowed file types
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".pdf"}
ALLOWED_CONTENT_TYPES = {
    "image/jpeg",
    "image/png",
    "application/pdf",
}

# Max upload size — 20 MB
MAX_FILE_SIZE_BYTES = 20 * 1024 * 1024


def get_storage_dir() -> Path:
    """Return the storage directory, creating it if it doesn't exist."""
    path = Path(settings.STORAGE_DIR)
    path.mkdir(parents=True, exist_ok=True)
    return path


def build_image_path(plan_id: UUID, ext: str) -> Path:
    """Build the full path for a floor plan image."""
    return get_storage_dir() / f"{plan_id}{ext}"


def save_image(data: bytes, plan_id: UUID, ext: str) -> str:
    """
    Write raw image bytes to disk.
    Returns the path string stored in the DB.
    """
    path = build_image_path(plan_id, ext)
    path.write_bytes(data)
    return str(path)


def read_image(image_path: str) -> bytes:
    """Read image bytes from disk — used by the Gemini extractor."""
    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"Floor plan image not found: {image_path}")
    return path.read_bytes()


def get_extension(filename: str) -> str:
    """Extract and validate file extension."""
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file type '{ext}'. "
            f"Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    return ext