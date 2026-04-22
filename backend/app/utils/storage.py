"""File storage utility (Supabase Storage / local fallback)."""

from __future__ import annotations

import secrets
from pathlib import Path

from app.config import get_settings

settings = get_settings()

ALLOWED_EXTENSIONS = {".pdf", ".docx"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

# Magic-byte signatures keyed by allowed extension. Validating these alongside
# the extension prevents extension-spoofed uploads (e.g. an EXE renamed to .pdf).
_MAGIC_BYTES: dict[str, tuple[bytes, ...]] = {
    ".pdf": (b"%PDF-",),
    # DOCX is an OOXML zip container.
    ".docx": (b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08"),
}


def validate_resume_file(filename: str, size: int) -> None:
    """Validate file extension and size. Raises ValueError on failure."""
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file type '{ext}'. Accepted: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    if size <= 0:
        raise ValueError("Empty file uploaded.")
    if size > MAX_FILE_SIZE:
        raise ValueError(f"File too large ({size / 1024 / 1024:.1f}MB). Max: 10MB")


def validate_resume_content(filename: str, content: bytes) -> None:
    """Verify file magic bytes match the declared extension.

    Call after `validate_resume_file` and before persisting/parsing.
    Raises ValueError on mismatch.
    """
    ext = Path(filename).suffix.lower()
    signatures = _MAGIC_BYTES.get(ext)
    if not signatures:
        # Already rejected by validate_resume_file, but be defensive.
        raise ValueError(f"Unsupported file type '{ext}'.")
    if not any(content.startswith(sig) for sig in signatures):
        raise ValueError(
            f"File content does not match declared type '{ext}'. Upload rejected."
        )


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
