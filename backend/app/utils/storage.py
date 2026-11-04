"""File storage utility (Supabase Storage / local fallback)."""

from __future__ import annotations

import secrets
import io
import zipfile
from fastapi import HTTPException
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

    if ext == ".docx":
        validate_docx_container(content)


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


async def read_resume_upload(upload) -> bytes:
    """Bound reads even when size/content-length is unavailable or dishonest."""
    if upload.size is not None and upload.size > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="Resume exceeds 10 MiB")
    content = bytearray()
    while True:
        chunk = await upload.read(min(64 * 1024, MAX_FILE_SIZE + 1 - len(content)))
        if not chunk:
            break
        content.extend(chunk)
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(status_code=413, detail="Resume exceeds 10 MiB")
    try:
        validate_resume_file(upload.filename or "", len(content))
        validate_resume_content(upload.filename or "", bytes(content))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    return bytes(content)


def validate_docx_container(content: bytes) -> None:
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            entries = archive.infolist()
            if len(entries) > 128 or len({e.filename for e in entries}) != len(entries):
                raise ValueError("DOCX contains too many or duplicate archive entries")
            names = {e.filename for e in entries}
            if not {"[Content_Types].xml", "word/document.xml"}.issubset(names):
                raise ValueError("File is not a DOCX document")
            total = 0
            for entry in entries:
                total += entry.file_size
                if total > 20 * 1024 * 1024 or entry.file_size > 8 * 1024 * 1024:
                    raise ValueError("DOCX expanded size exceeds limits")
                if entry.flag_bits & 1 or entry.file_size > max(entry.compress_size, 1) * 100:
                    raise ValueError("DOCX encryption or compression ratio exceeds limits")
                if entry.filename.endswith((".xml", ".rels")):
                    xml = archive.read(entry)
                    if b"<!DOCTYPE" in xml.upper() or b"<!ENTITY" in xml.upper():
                        raise ValueError("DOCX entity declarations are forbidden")
    except (zipfile.BadZipFile, RuntimeError, OSError):
        raise ValueError("Invalid DOCX archive") from None
