"""Resume service: file parsing (PDF/DOCX) + LLM extraction."""

from __future__ import annotations

import io
import json

import pdfplumber
from docx import Document as DocxDocument
from openai import AsyncOpenAI, OpenAI

from app.config import get_settings
from app.services.prompts import RESUME_EXTRACTION_PROMPT

_settings = get_settings()

SUPPORTED_EXTENSIONS = {".pdf", ".docx"}


def extract_text_from_bytes(content: bytes, filename: str) -> str:
    """Extract text from resume file bytes. Supports PDF and DOCX.

    Raises ValueError if format unsupported or no text extracted.
    """
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if ext == "pdf":
        return _extract_pdf(content)
    elif ext == "docx":
        return _extract_docx(content)
    else:
        raise ValueError(f"Unsupported file type '.{ext}'. Accepted: PDF, DOCX")


def _extract_pdf(content: bytes) -> str:
    """Extract text from PDF bytes using pdfplumber."""
    pages: list[str] = []
    with pdfplumber.open(io.BytesIO(content)) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                pages.append(text)

    if not pages:
        raise ValueError("No text could be extracted from PDF. Is this a scanned/image PDF?")
    return "\n\n".join(pages)


def _extract_docx(content: bytes) -> str:
    """Extract text from DOCX bytes using python-docx."""
    doc = DocxDocument(io.BytesIO(content))
    paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]

    if not paragraphs:
        raise ValueError("No text could be extracted from DOCX. Is the document empty?")
    return "\n\n".join(paragraphs)


def parse_resume_with_llm(
    client: OpenAI, resume_text: str
) -> tuple[dict, int, int]:
    """Send resume text to LLM, return (structured_data, prompt_tokens, completion_tokens)."""
    prompt = RESUME_EXTRACTION_PROMPT.format(resume_text=resume_text)
    response = client.chat.completions.create(
        model=_settings.active_llm_model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
    )
    raw = response.choices[0].message.content or ""
    cleaned = _strip_code_fences(raw)
    data = json.loads(cleaned)

    pt = response.usage.prompt_tokens if response.usage else 0
    ct = response.usage.completion_tokens if response.usage else 0
    return data, pt, ct


async def parse_resume_with_llm_async(
    client: AsyncOpenAI, resume_text: str
) -> tuple[dict, int, int]:
    """Async version: send resume text to LLM with provider fallback.

    Returns (structured_data, prompt_tokens, completion_tokens).
    """
    from app.services.llm_client import llm_chat_completion

    prompt = RESUME_EXTRACTION_PROMPT.format(resume_text=resume_text)
    response, _model = await llm_chat_completion(
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
    )
    raw = response.choices[0].message.content or ""
    cleaned = _strip_code_fences(raw)
    data = json.loads(cleaned)

    pt = response.usage.prompt_tokens if response.usage else 0
    ct = response.usage.completion_tokens if response.usage else 0
    return data, pt, ct


def _strip_code_fences(text: str) -> str:
    """Remove markdown code fences if present."""
    text = text.strip()
    if text.startswith("```"):
        first_nl = text.index("\n")
        text = text[first_nl + 1:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()
