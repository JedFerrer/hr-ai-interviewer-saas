"""Resume service: file parsing (PDF/DOCX) + LLM extraction."""

from __future__ import annotations

import io
import json

import pdfplumber
from docx import Document as DocxDocument
from openai import AsyncOpenAI, OpenAI

from app.config import get_settings
from app.services.llm_utils import strip_code_fences
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
    cleaned = strip_code_fences(raw)
    data = json.loads(cleaned)

    pt = response.usage.prompt_tokens if response.usage else 0
    ct = response.usage.completion_tokens if response.usage else 0
    return data, pt, ct


async def parse_resume_with_llm_async(
    client: AsyncOpenAI, resume_text: str
) -> tuple[dict, int, int]:
    """Async version: send resume text to LLM with provider fallback.

    Returns (validated_resume_dict, prompt_tokens, completion_tokens).

    The raw LLM JSON is validated through `ResumeData` so callers always get a
    normalized shape; invalid payloads raise ValueError (caught upstream).
    """
    from app.schemas.resume import ResumeData
    from app.services.llm_client import llm_chat_completion

    prompt = RESUME_EXTRACTION_PROMPT.format(resume_text=resume_text)
    response, _model = await llm_chat_completion(
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        json_mode=True,
    )
    raw = response.choices[0].message.content or ""
    cleaned = strip_code_fences(raw)
    raw_data = json.loads(cleaned)
    if not isinstance(raw_data, dict):
        raise ValueError("LLM did not return a JSON object for resume data")

    try:
        validated = ResumeData.model_validate(raw_data)
    except Exception as exc:  # ValidationError -> normalize to ValueError
        raise ValueError(f"Resume data failed validation: {exc}") from exc
    data = validated.model_dump()

    pt = response.usage.prompt_tokens if response.usage else 0
    ct = response.usage.completion_tokens if response.usage else 0
    return data, pt, ct


