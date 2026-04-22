"""Resume parser: PDF/DOCX text extraction → structured ResumeData via LLM."""

from __future__ import annotations

from pathlib import Path

import pdfplumber
from docx import Document as DocxDocument
from openai import OpenAI

from src.prompts import RESUME_EXTRACTION_PROMPT
from src.schemas import ResumeData
from src.utils import chat_completion_json

SUPPORTED_EXTENSIONS = {".pdf", ".docx"}


def extract_text_from_resume(file_path: str | Path) -> str:
    """Extract raw text from a PDF or DOCX file.

    Raises FileNotFoundError if the file does not exist.
    Raises ValueError if the format is unsupported or no text could be extracted.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Resume file not found: {path}")

    suffix = path.suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Unsupported file format '{suffix}'. Accepted: {', '.join(SUPPORTED_EXTENSIONS)}")

    if suffix == ".pdf":
        return _extract_from_pdf(path)
    return _extract_from_docx(path)


def _extract_from_pdf(path: Path) -> str:
    """Extract text from a PDF file using pdfplumber."""
    pages: list[str] = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                pages.append(text)

    if not pages:
        raise ValueError(f"No text could be extracted from {path}. Is this a scanned/image PDF?")
    return "\n\n".join(pages)


def _extract_from_docx(path: Path) -> str:
    """Extract text from a DOCX file using python-docx."""
    doc = DocxDocument(str(path))
    paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]

    if not paragraphs:
        raise ValueError(f"No text could be extracted from {path}. Is the document empty?")
    return "\n\n".join(paragraphs)


# Keep backward-compatible alias
extract_text_from_pdf = extract_text_from_resume


def parse_resume(client: OpenAI, resume_text: str) -> ResumeData:
    """Send raw resume text to LLM and return validated ResumeData.

    The LLM extracts structured fields (name, skills, experience, etc.)
    and the response is validated through the Pydantic schema.
    """
    prompt = RESUME_EXTRACTION_PROMPT.format(resume_text=resume_text)
    data = chat_completion_json(
        client,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        operation="resume_extraction",
    )
    return ResumeData.model_validate(data)
