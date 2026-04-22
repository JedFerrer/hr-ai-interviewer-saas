"""File storage utility (Supabase Storage / local fallback)."""

from __future__ import annotations

import secrets
from pathlib import Path

from app.config import get_settings

settings = get_settings()

ALLOWED_EXTENSIONS = {".pdf", ".docx"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


def validate_resume_file(filename: str, size: int) -> None:
    """Validate file extension and size. Raises ValueError on failure."""
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file type '{ext}'. Accepted: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    if size > MAX_FILE_SIZE:
        raise ValueError(f"File too large ({size / 1024 / 1024:.1f}MB). Max: 10MB")


def generate_storage_key(filename: str) -> str:
    """Generate a unique storage key for a resume file."""
    ext = Path(filename).suffix.lower()
    token = secrets.token_hex(16)
    return f"resumes/{token}{ext}"


async def upload_file_local(content: bytes, storage_key: str) -> str:
    """Save file to local storage (dev fallback). Returns the file path."""
    path = Path("uploads") / storage_key
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return str(path)
